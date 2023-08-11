from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import ConfigSpace as CS

from smac import MultiFidelityFacade as MFFacade
from smac import Scenario
from smac.intensifier.hyperband import Hyperband

from benchmark_simulator import ObjectiveFuncWrapper

from src.utils import get_bench_instance, get_save_dir_name, parse_args


class SMACObjectiveFuncWrapper(ObjectiveFuncWrapper):
    def __call__(
        self,
        config: CS.Configuration,
        budget: int,
        seed: int | None = None,
        data_to_scatter: dict[str, Any] | None = None,
    ) -> float:
        data_to_scatter = {} if data_to_scatter is None else data_to_scatter
        eval_config = dict(config)
        output = super().__call__(eval_config, fidels={self.fidel_keys[0]: int(budget)}, **data_to_scatter)
        return output[self.obj_keys[0]]


def run_smac(
    obj_func: Any,
    config_space: CS.ConfigurationSpace,
    save_dir_name: str,
    min_fidel: int,
    max_fidel: int,
    fidel_key: list[str],
    seed: int,
    n_workers: int,
    tmp_dir: str | None,
    n_init_min: int = 5,
    n_evals: int = 450,  # eta=3,S=2,100 full evals
) -> None:
    n_actual_evals_in_opt = n_evals + n_workers
    scenario = Scenario(
        config_space,
        n_trials=n_actual_evals_in_opt,
        min_budget=min_fidel,
        max_budget=max_fidel,
        n_workers=n_workers,
        output_directory=Path(os.path.join("" if tmp_dir is None else tmp_dir, "smac3")),
    )
    wrapper = SMACObjectiveFuncWrapper(
        obj_func=obj_func,
        n_workers=n_workers,
        save_dir_name=save_dir_name,
        n_actual_evals_in_opt=n_actual_evals_in_opt,
        n_evals=n_evals,
        seed=seed,
        fidel_keys=[fidel_key],
        continual_max_fidel=max_fidel,
        tmp_dir=tmp_dir,
    )
    smac = MFFacade(
        scenario,
        wrapper.__call__,  # SMAC raises an error when using wrapper, so we use wrapper.__call__ instead.
        initial_design=MFFacade.get_initial_design(scenario, n_configs=max(n_init_min, n_workers)),
        intensifier=Hyperband(scenario, incumbent_selection="highest_budget"),
        overwrite=True,
    )
    data_to_scatter = None
    if hasattr(obj_func, "get_benchdata"):
        # This data is shared in memory, and thus the optimization becomes quicker!
        data_to_scatter = {"benchdata": obj_func.get_benchdata()}

    # data_to_scatter must be a keyword argument.
    smac.optimize(data_to_scatter=data_to_scatter)


if __name__ == "__main__":
    args = parse_args()
    save_dir_name = get_save_dir_name(args)
    bench = get_bench_instance(args, keep_benchdata=False)
    fidel_key = "epoch" if "epoch" in bench.fidel_keys else "z0"
    run_smac(
        obj_func=bench,
        config_space=bench.config_space,
        min_fidel=bench.min_fidels[fidel_key],
        max_fidel=bench.max_fidels[fidel_key],
        fidel_key=fidel_key,
        n_workers=args.n_workers,
        save_dir_name=os.path.join("smac", save_dir_name),
        seed=args.seed,
        tmp_dir=args.tmp_dir,
    )
