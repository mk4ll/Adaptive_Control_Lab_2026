"""
Single entry point for every experiment.

    python run.py check            # rig sanity check (run first, every session)
    python run.py lab1             # identification, validation, P/PI, load variation
    python run.py load --position middle   # load-pot test, one position per call (non-interactive)
    python run.py lab2 ... lab6    # adaptive labs (need lab1's model.json)
    python run.py all              # check + lab1 ... lab6 back to back

Options:
    --sim               use the simulated motors instead of the Arduino (dry run, faster than real time)
    --quick             shorter runs (useful to check that everything works)
    --long SECONDS      duration of the long constant-step experiments
    --disturbance PWM   add a bounded random input disturbance (labs 3-6)
    --skip-load         lab1: skip the manual load-potentiometer part

Results: results/<rig|sim>/<lab>_<timestamp>/summary.md  (+ CSV of every run and PNG plots)
"""
import argparse
import importlib

from lab.rig import open_rig

LABS = {
    "check": "experiments.check",
    "lab1": "experiments.lab1_identification",
    "load": "experiments.lab1_load",
    "lab2": "experiments.lab2_mit",
    "lab3": "experiments.lab3_mrac",
    "lab4": "experiments.lab4_adi",
    "lab5": "experiments.lab5_robust",
    "lab6": "experiments.lab6_angle",
    "extras": "experiments.extras",
}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("lab", choices=list(LABS) + ["all"])
    p.add_argument("--sim", action="store_true")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--long", type=float, default=None)
    p.add_argument("--disturbance", type=float, default=None)
    p.add_argument("--skip-load", action="store_true")
    p.add_argument("--position", default=None, help="load test: potentiometer position (minimum|middle|maximum)")
    p.add_argument("--part", default=None, help="extras: lab6rest | mitfine | mitlow | lab5dz | mraclong | all")
    p.add_argument("--skip", default="", help="extras lab6rest: comma-separated run names already done")
    p.add_argument("--mrac-long", type=float, default=None, help="extras mraclong: duration in seconds (default 1800)")
    args = p.parse_args()

    if args.quick:
        from lab import config
        config.ID_PWM_LEVELS = config.ID_PWM_LEVELS[::2] + [config.ID_PWM_LEVELS[-1]]
        config.RUN_TIME = 20.0

    names = [n for n in LABS if n not in ("load", "extras")] if args.lab == "all" else [args.lab]
    rig = open_rig(args.sim)
    try:
        for name in names:
            print(f"\n================ {name} ================")
            importlib.import_module(LABS[name]).main(rig, args.sim, args)
    except KeyboardInterrupt:
        print("\nInterrupted - motor stopped.")
    finally:
        rig.close()


if __name__ == "__main__":
    main()
