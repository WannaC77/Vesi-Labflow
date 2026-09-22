#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S8-GATE-v1.1 机器化核对脚本（Vesi 多赛道）

判定规则唯一权威正本: <校准台账> 的《放行判定规则》S8-GATE-v1.1 §5.1/§5.2
输入模板: scripts/s8-gate-v1.1.check.yaml（复制后填写本轮四个分件成绩单 + 跨件一致性 + 硬门）

判定式（2026-09-20 同步 §5.2 破坏性订正 + §5.4.1 独立轮锚条款）:
  ok_anchor(p) =
      if anchor_drift_mode == "现场复评": anchor_drift 非 null 且 abs(anchor_drift) <= 3.0
      elif anchor_drift_mode == "沿用":   anchor_review_last / anchor_review_round /
                                          anchor_review_age_rounds 必填；age < 3 且标准未升版
      else:                               未填/非法枚举 → 该成绩单作废
  ok_piece(p) = (round_type == "WB独立复现轮") and (wb_score >= 90.0)
                and (p0_closed == true) and ok_anchor(p)
  ok_bundle   = all(ok_piece(p) for p in pieces) and cross_doc 全过
                and 匿名 == true and 查重率 <= 20
  字段缺失（standard_version 缺失 / wb_score / p0_closed / anchor_drift_mode 为 null）→ 该成绩单作废
  升版证据: 沿用态可选携带 anchor_review_std_version；缺失 → 输出提示（不阻断，由人工按 §5.4.1 a3 负责）

用法:
  python s8_gate_v11_check.py <check.yaml>   # 核对（合体放行 exit 0；否则 exit 1）
  python s8_gate_v11_check.py --selftest     # 内置示例自测（全过 exit 0）

退出码: 0 = 合体放行 / 自测全过;  1 = 合体不放行 / 自测失败;  2 = 输入或环境错误
落盘: 2026-09-19（S8 扩建 Phase B）
"""
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

WB_ROUND = "WB独立复现轮"
PASS_LINE = 90.0      # 放行线（百分制）
DRIFT_MAX = 3.0       # 锚漂移容差（百分制，= ±0.3 十分制）
SIM_MAX = 20.0        # 查重率上限（%）
REQUIRED_PIECE_FIELDS = ("wb_score", "p0_closed")
DRIFT_MODES = ("现场复评", "沿用")   # §5.4.1；未填/非法枚举 → 该成绩单作废


def fmt_drift(v):
    if isinstance(v, (int, float)):
        return format(v, "+.1f")
    return str(v)


def ok_anchor(p, std_ver):
    """§5.4.1 锚条款判定。返回 (ok, reason, fatal)。

    fatal=True → 该成绩单应作废（字段缺失/非法枚举）；否则 ok 为锚判定结论。
    """
    mode = p.get("anchor_drift_mode")
    if mode is None:
        return False, "anchor_drift_mode 缺失（§5.4.1）", True
    if mode == "现场复评":
        if p.get("anchor_drift") is None:
            return False, "现场复评态缺 anchor_drift", True
        d = p["anchor_drift"]
        if abs(d) > DRIFT_MAX:
            return False, "锚漂移 {} 超 ±{}（百分制）".format(fmt_drift(d), DRIFT_MAX), False
        return True, "", False
    if mode == "沿用":
        miss = [k for k in ("anchor_review_last", "anchor_review_round",
                            "anchor_review_age_rounds") if p.get(k) is None]
        if miss:
            return False, "沿用态字段缺失: " + ", ".join(miss), True
        if p["anchor_review_age_rounds"] >= 3:
            return False, "沿用超期（age={} ≥3）→ 须现场复评".format(p["anchor_review_age_rounds"]), False
        sv = p.get("anchor_review_std_version")
        if sv is not None and sv != std_ver:
            return False, "标准已升版（复评时 {} ≠ 现行 {}）→ 须现场复评".format(sv, std_ver), False
        if sv is None:
            return True, "沿用警告: 未携带 anchor_review_std_version，升版证据请人工确认（§5.4.1 a3）", False
        return True, "", False
    return False, "非法 anchor_drift_mode: {}".format(mode), True


def evaluate(cfg):
    """执行 v1.1 判定。返回 (results, text)。

    results = {
      'pieces': [{'id','verdict','reason'}, ...],   # verdict ∈ {放行,不放行,作废,不计入判定}
      'cross_doc_ok': bool, 'hard_gates_ok': bool, 'bundle_ok': bool, 'reasons': [...]
    }
    """
    cfg = cfg or {}
    pieces = cfg.get("pieces") or []
    round_type = cfg.get("round_type")
    std_ver = cfg.get("standard_version")
    wb_ok = (round_type == WB_ROUND)
    std_ok = std_ver is not None

    results = {"pieces": [], "bundle_ok": False, "reasons": [],
               "cross_doc_ok": False, "hard_gates_ok": False}
    lines = ["[S8-GATE-v1.1 机器化核对]",
             "gate_version: {}    standard_version: {}    round_type: {}".format(
                 cfg.get("gate_version"), std_ver, round_type)]
    if cfg.get("gate_version") not in (None, "S8-GATE-v1.1"):
        lines.append("  ⚠️ 注意: gate_version 非 S8-GATE-v1.1（本脚本仍按 v1.1 规则核对）")
    if not std_ok:
        lines.append("  ❌ standard_version 缺失 —— 没有版本号的分数不作数（全部成绩单作废）")

    # ---- 分件判定 ----
    lines.append("—— 分件判定 ——")
    for p in pieces:
        pid = p.get("id", "?")
        rec = {"id": pid, "verdict": None, "reason": ""}
        missing = [k for k in REQUIRED_PIECE_FIELDS if p.get(k) is None]
        if not std_ok:
            rec["verdict"], rec["reason"] = "作废", "standard_version 缺失（没有版本号的分数不作数）"
        elif missing:
            rec["verdict"], rec["reason"] = "作废", "字段缺失: " + ", ".join(missing)
        else:
            a_ok, a_reason, a_fatal = ok_anchor(p, std_ver)
            if a_fatal:
                rec["verdict"], rec["reason"] = "作废", a_reason
            elif not wb_ok:
                rec["verdict"], rec["reason"] = "不计入判定", "轮次类型={} 非「{}」".format(round_type, WB_ROUND)
            else:
                why = []
                if not (p["wb_score"] >= PASS_LINE):
                    why.append("放行分 {} < {}".format(p["wb_score"], PASS_LINE))
                if p["p0_closed"] is not True:
                    why.append("P0 未闭合")
                if not a_ok:
                    why.append(a_reason)
                rec["verdict"] = "放行" if not why else "不放行"
                rec["reason"] = "; ".join(why) if why else ("三项全过" + ("；" + a_reason if a_reason else ""))
        results["pieces"].append(rec)
        if p.get("anchor_drift_mode") == "沿用":
            drift_disp = "沿用·{}〔{}〕age={}".format(
                p.get("anchor_review_last"), p.get("anchor_review_round"),
                p.get("anchor_review_age_rounds"))
        else:
            drift_disp = fmt_drift(p.get("anchor_drift"))
        lines.append("{}: {}（score={}, p0={}, drift={}, mode={}, anchor={}） — {}".format(
            pid, rec["verdict"], p.get("wb_score"), p.get("p0_closed"),
            drift_disp, p.get("anchor_drift_mode"), p.get("anchor"), rec["reason"]))

    # ---- 跨件一致性 ----
    lines.append("—— 跨件一致性 ——")
    cd = cfg.get("cross_doc") or {}
    s7 = cd.get("s7_eight_items")
    prr = cd.get("paper_record_reconciliation") or {}
    cov = prr.get("覆盖率")
    fails = prr.get("不过项")
    p0s = cd.get("cross_piece_p0")
    cd_missing = [n for n, v in (("s7_eight_items", s7), ("覆盖率", cov),
                                 ("不过项", fails), ("cross_piece_p0", p0s)) if v is None]
    cd_ok = (not cd_missing) and (s7 == "PASS") and (cov == 100) \
        and (list(fails or []) == []) and (list(p0s or []) == [])
    results["cross_doc_ok"] = bool(cd_ok)
    lines.append("S7八项: {} | 记↔论对账: 覆盖率={}% 不过项={} | 跨件P0: {}".format(
        s7, cov, fails, p0s))
    if cd_missing:
        lines.append("  ❌ 跨件字段缺失: " + ", ".join(cd_missing) + " → 跨件一致性不通过")
    elif not cd_ok:
        bad = []
        if s7 != "PASS":
            bad.append("S7八项={}".format(s7))
        if cov != 100:
            bad.append("对账覆盖率={}%≠100%".format(cov))
        if list(fails or []):
            bad.append("不过项 {} 条".format(len(fails or [])))
        if list(p0s or []):
            bad.append("跨件P0 {} 条".format(len(p0s or [])))
        lines.append("  ❌ 跨件不一致: " + "; ".join(bad))
    else:
        lines.append("  ✅ 跨件一致性全过")

    # ---- 硬门 ----
    lines.append("—— 硬门 ——")
    hg = cfg.get("hard_gates") or {}
    anon = hg.get("匿名")
    dup = hg.get("查重率")
    hg_missing = [n for n, v in (("匿名", anon), ("查重率", dup)) if v is None]
    hg_ok = (not hg_missing) and (anon is True) and (dup is not None and dup <= SIM_MAX)
    results["hard_gates_ok"] = bool(hg_ok)
    lines.append("匿名: {} | 查重率: {}%".format(anon, dup))
    if hg_missing:
        lines.append("  ❌ 硬门字段缺失: " + ", ".join(hg_missing))
    elif not hg_ok:
        bad = []
        if anon is not True:
            bad.append("匿名未通过")
        if dup is None or dup > SIM_MAX:
            bad.append("查重率 {}% > {}%".format(dup, SIM_MAX))
        lines.append("  ❌ " + "; ".join(bad))
    else:
        lines.append("  ✅ 硬门全过")

    # ---- 合体判定 ----
    if len(pieces) != 4:
        results["reasons"].append("分件数={}≠4".format(len(pieces)))
    not_pass = ["{}:{}".format(r["id"], r["verdict"]) for r in results["pieces"] if r["verdict"] != "放行"]
    if not_pass:
        results["reasons"].append("未放行分件: " + ", ".join(not_pass))
    if not cd_ok:
        results["reasons"].append("跨件一致性未过")
    if not hg_ok:
        results["reasons"].append("硬门未过")
    results["bundle_ok"] = bool((len(pieces) == 4) and not not_pass and cd_ok and hg_ok)

    lines.append("—— 合体判定 ——")
    if results["bundle_ok"]:
        lines.append("合体判定: 放行 ✅")
    else:
        lines.append("合体判定: 不放行 ❌ —— " + "; ".join(results["reasons"]))
    return results, "\n".join(lines)


# ---------------- 自测 ----------------

def _base_cfg():
    return {
        "gate_version": "S8-GATE-v1.1",
        "standard_version": "S8-STD-v1.4",
        "round_type": WB_ROUND,
        "pieces": [
            {"id": "综述", "wb_score": 91.2, "p0_closed": True, "anchor": 84.0,
             "anchor_drift_mode": "现场复评", "anchor_drift": 1.0},
            {"id": "设计", "wb_score": 90.5, "p0_closed": True, "anchor": 88.0,
             "anchor_drift_mode": "现场复评", "anchor_drift": -2.0},
            {"id": "记录", "wb_score": 93.0, "p0_closed": True, "anchor": 95.0,
             "anchor_drift_mode": "现场复评", "anchor_drift": 2.5,
             "record_fields": {"篇数": 22, "幕覆盖": "4/4", "日期链": "PASS", "上传合规率": 95}},
            {"id": "论文", "wb_score": 90.1, "p0_closed": True, "anchor": 89.0,
             "anchor_drift_mode": "现场复评", "anchor_drift": 0.5},
        ],
        "cross_doc": {"s7_eight_items": "PASS",
                       "paper_record_reconciliation": {"覆盖率": 100, "不过项": []},
                       "cross_piece_p0": []},
        "hard_gates": {"匿名": True, "查重率": 18.0},
    }


def selftest():
    passed = []

    def check(name, cond):
        print(("PASS" if cond else "FAIL") + " | " + name)
        if not cond:
            raise AssertionError(name)
        passed.append(name)

    # A 全过 → 四件放行 + 合体放行
    res, txt = evaluate(_base_cfg())
    check("A1 全过→四件全放行", all(r["verdict"] == "放行" for r in res["pieces"]))
    check("A2 全过→合体放行", res["bundle_ok"] is True and "合体判定: 放行" in txt)

    # B 分件低于放行线
    cfg = _base_cfg(); cfg["pieces"][1]["wb_score"] = 88.5
    res, _ = evaluate(cfg)
    check("B1 设计88.5→不放行", res["pieces"][1]["verdict"] == "不放行")
    check("B2 分件不过→合体不放行", res["bundle_ok"] is False)

    # C 字段缺失 → 作废
    cfg = _base_cfg(); cfg["pieces"][2]["wb_score"] = None
    res, _ = evaluate(cfg)
    check("C1 记录缺wb_score→作废", res["pieces"][2]["verdict"] == "作废")
    check("C2 作废→合体不放行", res["bundle_ok"] is False)

    # D 非 WB 轮 → 不计入判定
    cfg = _base_cfg(); cfg["round_type"] = "同会话自评轮"
    res, _ = evaluate(cfg)
    check("D1 非WB轮→不计入判定", all(r["verdict"] == "不计入判定" for r in res["pieces"]))
    check("D2 非WB轮→合体不放行", res["bundle_ok"] is False)

    # E 锚漂移超限
    cfg = _base_cfg(); cfg["pieces"][3]["anchor_drift"] = 3.5
    res, _ = evaluate(cfg)
    check("E1 论文漂移+3.5→不放行", res["pieces"][3]["verdict"] == "不放行")

    # F 硬门不过（查重率 > 20）
    cfg = _base_cfg(); cfg["hard_gates"]["查重率"] = 21.0
    res, _ = evaluate(cfg)
    check("F1 查重21%→合体不放行", res["bundle_ok"] is False)

    # G 跨件一致性不过（S7 FAIL）
    cfg = _base_cfg(); cfg["cross_doc"]["s7_eight_items"] = "FAIL"
    res, _ = evaluate(cfg)
    check("G1 S7 FAIL→合体不放行", res["bundle_ok"] is False)

    # H standard_version 缺失 → 全部作废
    cfg = _base_cfg(); cfg["standard_version"] = None
    res, _ = evaluate(cfg)
    check("H1 无版本号→全部作废", all(r["verdict"] == "作废" for r in res["pieces"]))

    # J 沿用态合法（§5.4.1 a1/a2）→ 放行
    cfg = _base_cfg()
    cfg["pieces"][0].update({"anchor_drift_mode": "沿用", "anchor_drift": None,
                             "anchor_review_last": 84.0, "anchor_review_round": "R1综述 2026-09-09",
                             "anchor_review_age_rounds": 2})
    res, _ = evaluate(cfg)
    check("J1 沿用合法→放行", res["pieces"][0]["verdict"] == "放行")
    check("J2 沿用合法→合体仍放行", res["bundle_ok"] is True)

    # K 沿用超期（age≥3）→ 不放行
    cfg = _base_cfg()
    cfg["pieces"][0].update({"anchor_drift_mode": "沿用", "anchor_drift": None,
                             "anchor_review_last": 84.0, "anchor_review_round": "R1综述 2026-09-09",
                             "anchor_review_age_rounds": 3})
    res, _ = evaluate(cfg)
    check("K1 沿用age=3→不放行", res["pieces"][0]["verdict"] == "不放行")

    # L 缺 anchor_drift_mode → 作废
    cfg = _base_cfg(); cfg["pieces"][3].pop("anchor_drift_mode")
    res, _ = evaluate(cfg)
    check("L1 缺mode→作废", res["pieces"][3]["verdict"] == "作废")
    check("L2 缺mode→合体不放行", res["bundle_ok"] is False)

    # M 沿用态缺来源字段 → 作废
    cfg = _base_cfg()
    cfg["pieces"][0].update({"anchor_drift_mode": "沿用", "anchor_drift": None,
                             "anchor_review_age_rounds": 1})
    res, _ = evaluate(cfg)
    check("M1 沿用缺last/round→作废", res["pieces"][0]["verdict"] == "作废")

    # I 模板文件可解析（如 yaml 模块与模板均在）
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "s8-gate-v1.1.check.yaml")
    if yaml is not None and os.path.exists(tpl):
        with open(tpl, encoding="utf-8-sig") as f:
            tpl_cfg = yaml.safe_load(f)
        res, txt2 = evaluate(tpl_cfg)
        check("I1 模板可解析且输出完整", len(res["pieces"]) == len(tpl_cfg["pieces"])
              and "合体判定" in txt2)
    else:
        print("SKIP | I1 模板解析（缺 yaml 模块或模板文件）")

    print("-" * 56)
    print("SELFTEST OK — {} 项断言全过".format(len(passed)))
    return 0


# ---------------- 入口 ----------------

def main(argv):
    reconf = getattr(sys.stdout, "reconfigure", None)
    if reconf is not None:
        try:
            reconf(encoding="utf-8")
        except Exception:
            pass

    if "--selftest" in argv:
        try:
            return selftest()
        except AssertionError:
            print("SELFTEST FAIL")
            return 1

    args = [a for a in argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        return 2
    path = args[0]
    if yaml is None:
        print("错误: 需要 PyYAML（pip install pyyaml）")
        return 2
    try:
        with open(path, encoding="utf-8-sig") as f:
            cfg = yaml.safe_load(f)
    except Exception as e:
        print("错误: 无法读取/解析 {}: {}".format(path, e))
        return 2
    try:
        res, txt = evaluate(cfg)
    except Exception as e:
        print("错误: 判定执行失败（输入结构异常）: {}".format(e))
        return 2
    print(txt)
    return 0 if res["bundle_ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
