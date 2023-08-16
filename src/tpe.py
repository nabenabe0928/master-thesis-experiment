from __future__ import annotations

import os

import optuna

from src.utils import get_bench_instance, get_save_dir_name, parse_args, run_optuna


if __name__ == "__main__":
    args = parse_args()
    save_dir_name = get_save_dir_name(args)
    bench = get_bench_instance(args, use_fidel=False)
    run_optuna(
        obj_func=bench,
        config_space=bench.config_space,
        n_workers=args.n_workers,
        save_dir_name=os.path.join("tpe", save_dir_name),
        seed=args.seed,
        sampler=optuna.samplers.TPESampler(),
        tmp_dir=args.tmp_dir,
    )