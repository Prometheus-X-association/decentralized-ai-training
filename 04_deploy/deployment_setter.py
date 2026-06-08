import argparse

FILE_LIST = [
    "./aggregator/Dockerfile",
    "./aggregator/agg_runner.sh",
    "./orchestrator/orchestrator_runner.sh",
]

CLUSTER_DEPLOY_PREFIX = "#if cluster:"
TEST_DEPLOY_PREFIX = "#if test_deploy:"

def main():
    parser = argparse.ArgumentParser(description="Deployment Setter")
    parser.add_argument("--cluster-deploy", action="store_true", help="Set deployment for cluster")
    parser.add_argument("--test-deploy", action="store_true", help="Set deployment for test deployment")
    args = parser.parse_args()

    if not args.cluster_deploy and not args.test_deploy:
        print("Please specify either --cluster-deploy or --test-deploy")
        return

    for file_path in FILE_LIST:
        with open(file_path, "r") as file:
            lines = file.readlines()

        with open(file_path, "w") as file:
            file.write(lines[0])  # Write the first line as is

            for i in range(len(lines)-1):
                if lines[i].startswith(CLUSTER_DEPLOY_PREFIX) and args.cluster_deploy:
                    if lines[i+1].startswith("#"):
                        file.write(lines[i+1][1:])  # Write the line without the comment character
                    else:
                        file.write(lines[i+1])  # Write the original line if it's not commented
                elif lines[i].startswith(TEST_DEPLOY_PREFIX) and args.cluster_deploy:
                    if not(lines[i+1].startswith("#")):
                        file.write("#"+lines[i+1])  # Write the line with the comment character
                    else:
                        file.write(lines[i+1])  # Write the original line if it's already commented
                elif lines[i].startswith(TEST_DEPLOY_PREFIX) and args.test_deploy:
                    if lines[i+1].startswith("#"):
                        file.write(lines[i+1][1:])  # Write the line without the comment character
                    else:
                        file.write(lines[i+1])  # Write the original line if it's not commented
                elif lines[i].startswith(CLUSTER_DEPLOY_PREFIX) and args.test_deploy:
                    if not(lines[i+1].startswith("#")):
                        file.write("#"+lines[i+1])  # Write the line with the comment character
                    else:
                        file.write(lines[i+1])  # Write the original line if it's already commented
                else:
                    file.write(lines[i+1])  # Write the original line if it doesn't match any condition

if __name__ == "__main__":
    main()