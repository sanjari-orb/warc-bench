import yaml
import fire
from orby.digitalagent.utils import file_utils
from orby.digitalagent.evaluation import eval_runner
from orby.digitalagent.evaluation.eval_config import EvalConfig


def main(
    yaml_path: str,
    use_wa_service: bool = False,
    elastic_client: bool = False,
    docker_client: bool = False,
    subprocess: bool = False,
    max_ips: int = -1,
):
    with file_utils.open(yaml_path, "r") as f:
        config = EvalConfig(**yaml.safe_load(f.read()))
    if subprocess and (elastic_client or docker_client):
        raise ValueError(
            "subprocess is a part of elastic_client and docker_client, they cannot be used together."
        )
    if subprocess and not use_wa_service:
        raise ValueError("subprocess can only be used with use_wa_service.")
    if elastic_client:
        results = eval_runner.run_eval_with_elastic_client(
            config, use_docker=False, max_ips=max_ips
        )
    elif docker_client:
        results = eval_runner.run_eval_with_elastic_client(
            config, use_docker=True, max_ips=max_ips
        )
    elif use_wa_service:
        results = eval_runner.run_eval_with_wa_service(
            config, subprocess=subprocess, max_ips=max_ips
        )
    else:
        results = eval_runner.run_eval(config)
    print(results)
    print(results.to_json())


if __name__ == "__main__":
    fire.Fire(main)
