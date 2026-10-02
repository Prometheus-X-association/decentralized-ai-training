class AggregationTreeProcessor:
    def __process_aggregation_tree_data_processors(self):
        self.data_processors = []
        for proc in self.aggregation_tree["processors"]:
            dp = {
                "dp_uri": proc["uri"],
                "train_data_uri": proc["train_data_uri"],
                "forward_model_to": proc["forward_model_to"]
            }
            self.data_processors.append(dp)

    def __process_aggregation_tree_aggregators(self):
        self.aggregator_levels = []
        self.top_level_aggregator = None
        for agg in self.aggregation_tree["aggregators"]:
            if agg["top_level_aggregator"]:
                self.top_level_aggregator = {
                    "agg_uri": agg["uri"]
                }
            else:
                level = agg["aggregation_level"]
                while len(self.aggregator_levels) <= level:
                    self.aggregator_levels.append([])
                aggregator = {
                    "agg_uri": agg["uri"],
                    "forward_model_to": agg["forward_model_to"]
                }
                self.aggregator_levels[level].append(aggregator)

    def __process_model_forwarding(self, model_sources, model_ids):
        target_map = {}
        for i, source_url in enumerate(model_sources):
            source = None
            #searching for the source in the aggregation tree:
            ii = 0
            while ii < len(self.aggregation_tree["processors"]) and self.aggregation_tree["processors"][ii]["uri"] != source_url:
                ii += 1
            if ii < len(self.aggregation_tree["processors"]):
                source = self.aggregation_tree["processors"][ii]
            else:
                level = 0
                found = False
                while level < len(self.aggregator_levels) and not found:
                    ii = 0
                    while ii < len(self.aggregator_levels[level]) and self.aggregator_levels[level][ii]["agg_uri"] != source_url:
                        ii += 1
                    if ii < len(self.aggregator_levels[level]):
                        source = self.aggregator_levels[level][ii]
                        found = True
                    else:
                        level += 1

            if source is None:
                raise ValueError(f"Source URL {source_url} not found in aggregation tree")
            
            if len(source["forward_model_to"]) == 1:
                target = source["forward_model_to"][0]
                if target not in target_map:
                    target_map[target] = []
                target_map[target].append(model_ids[i])
            else:
                for k in range(len(model_ids[i])):
                    model_id = model_ids[i][k]
                    target = source["forward_model_to"][k]
                    if target not in target_map:
                        target_map[target] = []
                    target_map[target].append(model_id)
        return target_map


    def __init__(self, aggregation_tree):
            self.aggregation_tree = aggregation_tree
            self.__process_aggregation_tree_data_processors()
            self.__process_aggregation_tree_aggregators()

    def get_data_processor_configs(self,
                                   global_model_host,
                                   global_model_id,
                                   global_model_user,
                                   global_model_password):
        processors = []
        for proc in self.data_processors:
            dp_config = proc.copy()
            dp_config.update({
                "global_model_host": global_model_host,
                "global_model_id": global_model_id,
                "global_model_user": global_model_user,
                "global_model_password": global_model_password
            })
            processors.append(dp_config)
        return processors

    def get_aggregator_level(self,
                             level: int,
                             model_sources: list,
                             model_ids: list,
                             local_data_sizes: list =  [],
                             global_model_host: str = "",
                             global_model_id: str = "",
                             global_model_user: str = "",
                             global_model_password: str = ""):
        '''
        Retrieve the aggregator configuration for a specific level.

        parameters:
            level (int): The aggregation level.
            model_sources (list): List of model sources.
            model_ids (list): Nested list of model IDs, where each sublist corresponds to a model source.
            local_data_sizes (list, optional): List of local data sizes. Defaults to []. Used for FedAvg on the first level of aggregation.
            global_model_host (str, optional): Host for the global model. Defaults to "". Used for DeltaRep only.
            global_model_id (str, optional): ID for the global model. Defaults to "". Used for DeltaRep only.
            global_model_user (str, optional): User for the global model. Defaults to "". Used for DeltaRep only.
            global_model_password (str, optional): Password for the global model. Defaults to "". Used for DeltaRep only.

        returns:
            list: List of aggregator configurations for the specified level.
        '''
        if level < 0 or level >= len(self.aggregator_levels):
            raise ValueError(f"Invalid aggregation level: {level}")
        target_map = self.__process_model_forwarding(model_sources, model_ids)
        print(target_map)
        agg_configs = []
        for agg in self.aggregator_levels[level]:
            agg_config = agg.copy()
            agg_config.update({
                "model_sources": model_sources,
                "model_ids": target_map.get(agg["agg_uri"], []),
                "local_data_sizes": local_data_sizes if len(local_data_sizes) > 0 else [1] * len(target_map.get(agg["agg_uri"], [])),
                "global_model_host": global_model_host,
                "global_model_id": global_model_id,
                "global_model_user": global_model_user,
                "global_model_password": global_model_password,
                "aggregation_algorithm": self.aggregation_tree.get("aggregation_algorithm", "fedavg")
            })
            agg_configs.append(agg_config)
        return agg_configs

    def get_level_counts(self):
        return len(self.aggregator_levels)

    def get_top_level_aggregator(self,
                                  model_sources: list,
                                  model_ids: list,
                                  local_data_sizes: list = []):
        if not self.top_level_aggregator:
            raise ValueError("No top-level aggregator found")
        agg_config = self.top_level_aggregator.copy()
        agg_config.update({
            "model_sources": model_sources,
            "model_ids": model_ids,
            "local_data_sizes": local_data_sizes if len(local_data_sizes) > 0 else [1] * len(model_ids),
            "aggregation_algorithm": self.aggregation_tree.get("aggregation_algorithm", "fedavg")
        })
        return agg_config