# -*- coding: utf-8 -*-
"""剂量换算核对器：mg/kg ↔ mg/m² ↔ 人体等效剂量 HED + 单位等价检查。

适用场景
    动物实验剂量与人体剂量的换算核对：把某物种的 mg/kg 剂量换算为 mg/m²，或换算为
    人体等效剂量 HED（human equivalent dose）；把 HED 反算回动物剂量；以及浓度/质量
    单位的等价性自检（防止 mg/mL 与 mg/L 之类的单位混用错误）。

公式与口径声明（依据 FDA Guidance for Industry, 2005：
Estimating the Maximum Safe Starting Dose in Initial Clinical Trials...）
    1. Km（= 体重 kg / 体表面积 m²）为物种特定因子；本脚本用 FDA 表值：
       mouse 3, rat 6, hamster 5, guinea pig 8, rabbit 12, monkey 12, dog 20, human 37。
    2. mg/m² = mg/kg × Km
    3. HED(mg/kg) = 动物剂量(mg/kg) × Km_animal / Km_human   （Km_human = 37）
    4. 反算：动物剂量(mg/kg) = HED(mg/kg) × Km_human / Km_animal
    5. 推论（脚本会自检）：HED 的 mg/m² = 动物剂量的 mg/m²（体表面积归一化后跨物种等价）
    6. 局限：HED 仅为**起始剂量估算**的体表面积归一化方法；不等于安全剂量，
       也不替代毒理/PK 证据（如 NOAEL、AUC 暴露比对）。本脚本只做算术核对，
       不做安全性判断。
    7. 单位等价检查为**同量纲**比较：mg/mL ↔ μg/μL ↔ g/L 等价（均为 1 mg/mL）；
       mg/mL 与 mg/L、ng/mL 不等价（相差 10³、10⁶）。质量单位 mg 与 μg 不等价
       （1 mg = 1000 μg）。检查用相对容差 1e-9。

输入输出
    纯命令行工具，不读文件。输出换算结果 / 单位检查表（stdout）；--json 输出 JSON。
依赖
    numpy（仅用于数值容差判断；无 pandas/scipy/matplotlib）。
命令行示例
    python check_dose.py --selftest
    python check_dose.py --demo
    python check_dose.py --dose 5 --species rat --to hed
    python check_dose.py --dose 5 --species rat --to mgm2
    python check_dose.py --dose 5 --species rat --to all
    python check_dose.py --hed 0.8108 --species rat
    python check_dose.py --unit-check
"""

import argparse
import json
import sys

import numpy as np

# ============ 参数常量区（改这里 / 或用命令行覆盖）============
# FDA Km 因子表（体重 kg / 体表面积 m²）
KM_TABLE = {
    "mouse": 3.0,
    "rat": 6.0,
    "hamster": 5.0,
    "guinea pig": 8.0,
    "rabbit": 12.0,
    "monkey": 12.0,
    "dog": 20.0,
    "human": 37.0,
}
KM_HUMAN = KM_TABLE["human"]          # 37
# 物种名别名（输入归一化）
SPECIES_ALIASES = {
    "mice": "mouse", "mouses": "mouse", "小鼠": "mouse",
    "rats": "rat", "大鼠": "rat",
    "hamsters": "hamster", "仓鼠": "hamster",
    "guinea_pig": "guinea pig", "guineapig": "guinea pig", "guinea pigs": "guinea pig",
    "豚鼠": "guinea pig",
    "rabbits": "rabbit", "兔": "rabbit",
    "monkeys": "monkey", "猴": "monkey",
    "dogs": "dog", "犬": "dog",
    "human": "human", "humans": "human", "人": "human",
}
# 浓度单位 -> 基准 mg/mL 的换算系数
CONC_FACTORS_TO_MG_PER_ML = {
    "mg/mL": 1.0, "g/L": 1.0, "ug/uL": 1.0, "μg/μL": 1.0, "mg/ml": 1.0,
    "ug/mL": 1e-3, "μg/mL": 1e-3, "mg/L": 1e-3,
    "ng/mL": 1e-6, "ng/ml": 1e-6,
    "mg/dL": 1e-2, "ug/dL": 1e-5, "μg/dL": 1e-5,
}
# 质量单位 -> 基准 mg 的换算系数
MASS_FACTORS_TO_MG = {
    "g": 1e3, "mg": 1.0, "ug": 1e-3, "μg": 1e-3, "ng": 1e-6, "pg": 1e-9,
}
REL_TOL = 1e-9                        # 等价判定相对容差
UNIT_KINDS = ("conc", "mass")
# =============================================================


# ------------------------------------------------------------------
# 物种 / 换算
# ------------------------------------------------------------------
def normalize_species(name):
    """物种名归一化（大小写/别名/去空格）。"""
    key = str(name).strip().lower()
    key = SPECIES_ALIASES.get(key, key)
    if key not in KM_TABLE:
        raise SystemExit(f"[错误] 未知物种 {name!r}；可选：{sorted(KM_TABLE)}")
    return key


def km_of(species):
    """取物种 Km 值。"""
    return KM_TABLE[normalize_species(species)]


def mgkg_to_mgm2(dose_mg_kg, species):
    """mg/kg -> mg/m²：乘 Km（rat 的系数 = 6）。"""
    return float(dose_mg_kg) * km_of(species)


def mgm2_to_mgkg(dose_mg_m2, species):
    """mg/m² -> mg/kg：除 Km。"""
    return float(dose_mg_m2) / km_of(species)


def hed_mgkg(dose_mg_kg, species):
    """动物 mg/kg -> 人体等效剂量 HED(mg/kg) = 剂量 × Km_animal / Km_human。"""
    return float(dose_mg_kg) * km_of(species) / KM_HUMAN


def animal_mgkg_from_hed(hed_mg_kg, species):
    """HED(mg/kg) -> 该物种动物 mg/kg = HED × Km_human / Km_animal。"""
    return float(hed_mg_kg) * KM_HUMAN / km_of(species)


def convert_all(dose_mg_kg, species):
    """一次给出全部换算结果（mg/kg 输入口径）。"""
    sp = normalize_species(species)
    km = KM_TABLE[sp]
    dose = float(dose_mg_kg)
    return {
        "species": sp, "km": km, "km_human": KM_HUMAN, "dose_mg_kg": dose,
        "dose_mg_m2": dose * km,
        "hed_mg_kg": dose * km / KM_HUMAN,
        "hed_mg_m2": dose * km,                       # = 动物 mg/m²（跨物种等价）
        "animal_dose_mg_kg_from_hed": dose,           # 自身即动物剂量（自洽检查用）
    }


# ------------------------------------------------------------------
# 单位等价检查
# ------------------------------------------------------------------
def _factor(unit, kind):
    """取单位到基准的换算系数（conc -> mg/mL；mass -> mg）。"""
    table = CONC_FACTORS_TO_MG_PER_ML if kind == "conc" else MASS_FACTORS_TO_MG
    if unit not in table:
        raise SystemExit(f"[错误] 未知单位 {unit!r}（kind={kind}）；可选：{sorted(table)}")
    return table[unit]


def units_equivalent(u1, u2, kind="conc", tol=REL_TOL):
    """两个同量纲单位是否等价（相对容差 tol）。"""
    f1, f2 = _factor(u1, kind), _factor(u2, kind)
    return abs(f1 - f2) <= tol * max(abs(f1), abs(f2))


def unit_factor(u_from, u_to, kind="conc"):
    """u_from -> u_to 的数值换算系数（value_to = value_from × factor）。"""
    return _factor(u_from, kind) / _factor(u_to, kind)


def unit_check_rows():
    """单位等价检查用例表：[(u1, u2, kind, 期望等价, 说明)]。"""
    return [
        ("mg/mL", "g/L", "conc", True, "1 mg/mL = 1 g/L"),
        ("mg/mL", "ug/uL", "conc", True, "1 mg/mL = 1 μg/μL"),
        ("ug/mL", "mg/L", "conc", True, "1 μg/mL = 1 mg/L"),
        ("mg/mL", "mg/L", "conc", False, "相差 10³"),
        ("mg/mL", "ng/mL", "conc", False, "相差 10⁶"),
        ("mg", "ug", "mass", False, "相差 10³（1 mg = 1000 μg）"),
        ("g", "mg", "mass", False, "相差 10³"),
    ]


def run_unit_check():
    """跑单位等价检查并打印表格，返回 (失败数, 行列表)。"""
    rows = unit_check_rows()
    fails, out = 0, []
    print("=" * 78)
    print("单位等价检查（相对容差 %g）" % REL_TOL)
    print("=" * 78)
    print(f"{'单位 A':<10} {'单位 B':<10} {'类型':<6} {'实测':<6} {'期望':<6} 说明")
    print("-" * 78)
    for u1, u2, kind, expect, note in rows:
        got = units_equivalent(u1, u2, kind)
        ok = (got == expect)
        fails += (not ok)
        out.append({"u1": u1, "u2": u2, "kind": kind, "equivalent": bool(got),
                    "expected": bool(expect), "ok": bool(ok),
                    "factor": unit_factor(u1, u2, kind)})
        print(f"{u1:<10} {u2:<10} {kind:<6} "
              f"{('等价' if got else '不等价'):<6} {('等价' if expect else '不等价'):<6} "
              f"[{'PASS' if ok else 'FAIL'}] {note}")
    print("-" * 78)
    print("等价对计数：等价 " + str(sum(1 for r in rows if r[3])) +
          " 个 / 不等价 " + str(sum(1 for r in rows if not r[3])) + " 个")
    print("换算示例：1 mg/mL = " + f"{unit_factor('mg/mL', 'ng/mL', 'conc'):.0f} ng/mL；"
          f"1 mg = {unit_factor('mg', 'ug', 'mass'):.0f} μg")
    print(f"单位检查结果：{'全部 PASS' if fails == 0 else str(fails) + ' 项 FAIL'}")
    return fails, out


# ------------------------------------------------------------------
# 报告
# ------------------------------------------------------------------
def _fmt(x, nd=6):
    """数值格式化。"""
    if x is None:
        return "-"
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return "nan"
    return f"{x:.{nd}g}"


def report_conversion(res):
    """换算结果 Markdown 文本。"""
    lines = ["# 剂量换算核对", ""]
    lines.append(f"- 物种：{res['species']}（Km = {_fmt(res['km'], 4)}；"
                 f"人类 Km = {_fmt(res['km_human'], 4)}）")
    lines.append(f"- 输入剂量：{_fmt(res['dose_mg_kg'], 6)} mg/kg")
    lines.append("")
    lines.append("| 输出量 | 值 | 公式 |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| mg/m²（动物） | {_fmt(res['dose_mg_m2'], 6)} | 剂量 × Km_animal |")
    lines.append(f"| HED (mg/kg) | {_fmt(res['hed_mg_kg'], 6)} | 剂量 × Km_animal / Km_human |")
    lines.append(f"| HED (mg/m²) | {_fmt(res['hed_mg_m2'], 6)} | = 动物 mg/m²（体表面积归一） |")
    lines.append("")
    lines.append("口径声明：Km 取 FDA (2005) 指导原则表值；HED 仅为起始剂量估算方法，"
                 "不等于安全剂量，不替代 NOAEL / 暴露（AUC）比对等毒理证据。")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 自测 / 演示
# ------------------------------------------------------------------
def selftest():
    """known-answer：rat 5 mg/kg -> HED=0.8108 mg/kg；rat mg/m² 系数=6；单位等价用例。"""
    print("=" * 78)
    print("check_dose.py --selftest")
    print("known-answer：rat 5 mg/kg → HED = 5×6/37 = 0.810810... mg/kg；rat mg/m² 系数 = 6")
    print("=" * 78)
    n_fail = 0

    # --- 数值断言 ---
    hed = hed_mgkg(5.0, "rat")
    checks = [
        ("rat 5 mg/kg → HED (mg/kg)", hed, 0.8108, 0.1, "mg/kg"),
        ("rat 5 mg/kg → mg/m² 系数", mgkg_to_mgm2(5.0, "rat") / 5.0, 6.0, 0.1, "系数"),
        ("rat 5 mg/kg → mg/m²", mgkg_to_mgm2(5.0, "rat"), 30.0, 0.1, "mg/m²"),
        ("HED 的 mg/m² = 动物 mg/m²", convert_all(5.0, "rat")["hed_mg_m2"],
         mgkg_to_mgm2(5.0, "rat"), 1e-9, "mg/m²"),
        ("human 自身换算：HED = 剂量", hed_mgkg(7.5, "human"), 7.5, 1e-9, "mg/kg"),
        ("HED 反算回 rat 剂量（往返）", animal_mgkg_from_hed(hed, "rat"), 5.0, 1e-9, "mg/kg"),
        ("1 mg = 1000 μg 换算系数", unit_factor("mg", "ug", "mass"), 1000.0, 1e-9, "倍"),
        ("1 mg/mL = 1e6 ng/mL 换算系数", unit_factor("mg/mL", "ng/mL", "conc"), 1e6, 1e-9, "倍"),
    ]
    for name, meas, exp, tol_pct, unit in checks:
        err = abs(meas - exp) / abs(exp) * 100.0
        ok = err <= tol_pct
        n_fail += (not ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        print(f"        实测 = {_fmt(meas, 8)} {unit} | 期望 = {_fmt(exp, 8)} | "
              f"相对误差 = {err:.2e}% (容差 {tol_pct:g}%)")

    # --- 全物种公式一致性：HED = 剂量 × Km_animal / Km_human，且 mg/kg↔mg/m² 可往返 ---
    d_test = 3.0
    dev_hed = max(abs(hed_mgkg(d_test, sp) - d_test * km / KM_HUMAN) / (d_test * km / KM_HUMAN)
                  for sp, km in KM_TABLE.items())
    dev_rt = max(abs(mgm2_to_mgkg(mgkg_to_mgm2(d_test, sp), sp) - d_test) / d_test
                 for sp in KM_TABLE)
    ok = (dev_hed < 1e-12) and (dev_rt < 1e-12)
    n_fail += (not ok)
    print(f"[{'PASS' if ok else 'FAIL'}] 全物种公式一致性（HED 公式 + mg/kg↔mg/m² 往返，8 物种）")
    print(f"        HED 最大相对偏差 = {dev_hed:.3e}；往返最大相对偏差 = {dev_rt:.3e} | "
          f"期望 < 1e-12")

    # --- 单位等价用例（等价 / 不等价各 ≥2 个）---
    for u1, u2, kind, expect, note in unit_check_rows():
        got = units_equivalent(u1, u2, kind)
        ok = (got == expect)
        n_fail += (not ok)
        print(f"[{'PASS' if ok else 'FAIL'}] 单位{'等价' if expect else '不等价'}用例："
              f"{u1} vs {u2}（{kind}）")
        print(f"        实测 = {'等价' if got else '不等价'} | 期望 = "
              f"{'等价' if expect else '不等价'} | {note}")

    # --- Km 表完整性 ---
    km_fda = {"mouse": 3.0, "rat": 6.0, "hamster": 5.0, "guinea pig": 8.0,
              "rabbit": 12.0, "monkey": 12.0, "dog": 20.0, "human": 37.0}
    ok = (KM_TABLE == km_fda)
    n_fail += (not ok)
    print(f"[{'PASS' if ok else 'FAIL'}] Km 表与 FDA 表值一致（8 个物种）")
    print(f"        实测 = {KM_TABLE}")
    print(f"        期望 = {km_fda}")

    print("-" * 78)
    if n_fail == 0:
        print("selftest 结果：全部 PASS")
        return 0
    print(f"selftest 结果：{n_fail} 项 FAIL")
    return 1


def demo():
    """示例：rat 5 mg/kg 的 HED / mg/m² 换算 + 单位等价检查。"""
    print("### demo：rat 5 mg/kg（候选药物 X 脂质体大鼠给药剂量）换算")
    print()
    print(report_conversion(convert_all(5.0, "rat")))
    print()
    print("### 各物种同一 5 mg/kg 的 HED 一览")
    print()
    print("| 物种 | Km | mg/m² | HED (mg/kg) |")
    print("| --- | --- | --- | --- |")
    for sp, km in KM_TABLE.items():
        print(f"| {sp} | {_fmt(km, 3)} | {_fmt(mgkg_to_mgm2(5.0, sp), 6)} | "
              f"{_fmt(hed_mgkg(5.0, sp), 6)} |")
    print()
    run_unit_check()
    return 0


# ------------------------------------------------------------------
# 主程序
# ------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="剂量换算核对器：mg/kg ↔ mg/m² ↔ HED + 单位等价检查",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dose", type=float, help="动物剂量（mg/kg）")
    p.add_argument("--hed", type=float, help="人体等效剂量（mg/kg），用于反算动物剂量")
    p.add_argument("--species", default="rat", help=f"物种（默认 rat；可选 {sorted(KM_TABLE)}）")
    p.add_argument("--to", default="all", choices=("all", "hed", "mgm2", "mgkg"),
                   help="输出目标：all（默认）/ hed / mgm2 / mgkg（需配 --hed 反算）")
    p.add_argument("--unit-check", action="store_true", dest="unit_check",
                   help="运行单位等价检查")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    p.add_argument("--selftest", action="store_true", help="跑内置 known-answer 自测")
    p.add_argument("--demo", action="store_true", help="跑示例换算 + 单位检查")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.selftest:
        return selftest()
    if args.demo:
        return demo()
    if args.unit_check:
        fails, _ = run_unit_check()
        return 0 if fails == 0 else 1
    if args.hed is not None:
        sp = normalize_species(args.species)
        animal = animal_mgkg_from_hed(args.hed, sp)
        res = {"species": sp, "km": KM_TABLE[sp], "km_human": KM_HUMAN,
               "hed_mg_kg": float(args.hed), "animal_mg_kg": animal,
               "animal_mg_m2": animal * KM_TABLE[sp]}
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"物种 {sp}（Km={_fmt(res['km'], 3)}）：HED {_fmt(args.hed, 6)} mg/kg "
                  f"→ 动物剂量 {_fmt(animal, 6)} mg/kg = {_fmt(res['animal_mg_m2'], 6)} mg/m²")
            print("口径：动物 mg/kg = HED × Km_human / Km_animal；"
                  "HED 仅为起始剂量估算，非安全剂量")
        return 0
    if args.dose is None:
        build_parser().print_help()
        print("\n[提示] 需要 --dose 或 --hed，或使用 --selftest / --demo / --unit-check")
        return 2

    res = convert_all(args.dose, args.species)
    if args.to == "hed":
        out = {"species": res["species"], "dose_mg_kg": res["dose_mg_kg"],
               "hed_mg_kg": res["hed_mg_kg"],
               "formula": "HED = dose × Km_animal / Km_human"}
        print(json.dumps(out, ensure_ascii=False, indent=2) if args.json
              else f"{_fmt(res['dose_mg_kg'], 6)} mg/kg（{res['species']}）"
                   f" → HED = {_fmt(res['hed_mg_kg'], 6)} mg/kg "
                   f"[= 剂量 × {_fmt(res['km'], 3)}/{_fmt(res['km_human'], 3)}]")
    elif args.to == "mgm2":
        print(json.dumps({"species": res["species"], "dose_mg_kg": res["dose_mg_kg"],
                          "dose_mg_m2": res["dose_mg_m2"]}, ensure_ascii=False, indent=2)
              if args.json else
              f"{_fmt(res['dose_mg_kg'], 6)} mg/kg（{res['species']}）"
              f" → {_fmt(res['dose_mg_m2'], 6)} mg/m² [× Km = {_fmt(res['km'], 3)}]")
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
              else report_conversion(res))
        if args.json:
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
