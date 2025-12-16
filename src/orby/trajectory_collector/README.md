# Trajectory Collector

See [here](https://docs.google.com/document/d/1vNDGHY2FX-dofbD0PAusSZLUHxIuLSZ59DZSCESDD08/edit?usp=sharing) for the design document.

Trajectory collector attempts to use digital-agent to conduct guided web GUI interaction crawling. User should expect a `.pb` file for each data point stored on S3. For some sample data collected by the trajectory collector, see [this S3 folder](https://orby-osu-va.s3.us-east-1.amazonaws.com/trajectory_data/claude35_train_10/).

**NOTE:** In each `ActionData` in the `trajectory_data.actions`, Trajectory Collector only stores `after_state`. The `before_state` should be fetched from the `after_state` of the previous action. The first `ActionData` will always have `START_OF_TRAJECTORY` as its `action_data.browser_gym_action.action_string`.


## Code structure
- `orby/trajectory_collector` hosts the codebase for it.
- `tests/trajectory_collector` hosts its unit tests.
- `scripts/trajectory_collector` hosts scripts to initialize a crawling attempt.
- `experiments/trajectory_collector` hosts the post processining pipeline.


## Usage

### Local / single machine crawling
To run a local crawling session, **edit** and run the following file:
```{bash}
scripts/trajectory_collector/local_trajectory_collection.py
```

Fields to edit:
```{python}
controller = ParallelComputingController(
    source_parquet_path= ,  # Path to the coarse task data
    s3_save_uri=,  # Path to save the generated data
    num_raw_data=5,  # Number of trajectories to generate
    data_per_batch=16, # urls to crawl per linear batches
    request_per_minute=None,  # Number of requests per minute
    max_steps=15,  # Maximum number of steps for each task
    agent_name="basic",  # Name of the agent
    agent_model_provider="anthropic",  # Model provider of the agent
    agent_model_name="claude-3-5-sonnet-20241022",  # Model name of the agent
    temperature=0.0,  # Temperature for the agent model
    max_tokens=500,  # Maximum number of tokens for the agent model
    max_repetitive_actions=3,  # Maximum number of repetitive actions allowed before truncating the task
    dp_max_retries=3,  # Maximum number of retries for each raw data point
    timeout=None,  # Timeout for each task
    verbose=False,  # Whether to print verbose logs
)
```


### **(CURRENTLY NON-FUNCTIONAL)** multi-node crawling
To submit a remote job to a ray cluster, **edit** and use
```{bash}
cd scripts/trajectory_collector
./ray_job_submit.sh
```

Fields to edit:
```{bash}
SOURCE_S3_URI= # S3 URI to load the environment
SAVE_S3_URI= # S3 URI to save the collected trajectories
OPENAI_API_KEY= # OpenAI API Key
# Default values of the following parameters; reset with caution
MAX_TRAJS=100 # Number of trajectories to collect
MAX_STEPS=15 # Maximum number of steps per trajectory
```


### Post-processing
To start the post-process over a dataset, **edit** and run the following file
```{bash}
experiments/trajectory_collector/trajectory_post_process.py
```

Fields to edit
```{python}
# Edit the arguments as needed
args = {
    "read_s3_dir": "s3://orby-osu-va/trajectory_data/claude35_train_10/raw/",
    "write_s3_dir": "s3://orby-osu-va/trajectory_data/claude35_train_10/processed/",
    "model_provider": "anthropic",
    "model_name": "claude-3-5-sonnet-20241022",
    "verbose": False,
}
```
