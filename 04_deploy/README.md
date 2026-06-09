# Deployment

## Training data

Copy the training data into `02_data`,
e.g., `02_data/dp1/train_data.npz` and `02_data/dp2/train_data.npz`.

## Image building

For the first step, run the building script directly:

```bash
$ ./build_images.sh
```

After that, docker images can be rebuilt by `docker compose`:

```bash
$ docker compose build
```

## Local deployment

```bash
$ docker compsoe up
```

To tear down the setup, use

```bash
$ docker compose down
```

Also, to delete cache, use

```bash
$ docker compose down -v
```