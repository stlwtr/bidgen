from bidgen import fill

V = {
    "purchaser": "饶河县教育和体育局",
    "agency": "黑龙江省毅润项目管理有限公司",
    "project_name": "2026年饶河县中考考点基本办学条件改善项目",
    "project_code": "[230524]YRZB[GK]20260001",
    "company": "示例科技有限公司",
}


def test_purchaser_agency_line():
    assert (
        fill.fill_line("采购人、采购代理机构名称:", V)
        == "采购人、采购代理机构名称：饶河县教育和体育局、黑龙江省毅润项目管理有限公司"
    )


def test_project_code_bracket():
    assert fill.fill_line("（项目编号： ）", V) == "（项目编号：[230524]YRZB[GK]20260001）"
    assert fill.fill_line("(项目编号: )", V) == "（项目编号：[230524]YRZB[GK]20260001）"


def test_bidder_name_bracket():
    assert fill.fill_line("经我方(投标人名称)", V) == "经我方（投标人名称：示例科技有限公司）"
    assert fill.fill_line("系____(投标人名称)的", V) == "系____（投标人名称：示例科技有限公司）的"


def test_project_name_and_unit_brackets():
    assert fill.fill_line("参加 （单位名称）的 （项目名称）采购活动", V) == (
        "参加 （饶河县教育和体育局）的 （2026年饶河县中考考点基本办学条件改善项目）采购活动"
    )


def test_sentence_gap():
    # The tender template reads "按照已收到的 ____ 项目（项目编号：____）"; the
    # project name keeps the trailing "项目" word from the template.
    assert fill.fill_line("按照已收到的 项目(项目编号: )", V) == (
        "按照已收到的2026年饶河县中考考点基本办学条件改善项目项目（项目编号：[230524]YRZB[GK]20260001）"
    )


def test_untouched_when_no_match():
    assert fill.fill_line("特此承诺。", V) == "特此承诺。"


def test_build_values_placeholder():
    values = fill.build_values({}, {})
    assert values["purchaser"] == "______"
    assert values["company"] == "______"


def test_marked_spans_are_underlined_targets():
    parts = fill.split_markup(fill.fill_marked("（项目编号： ）", V))
    assert ("[230524]YRZB[GK]20260001", True) in parts

    parts = fill.split_markup(fill.fill_marked("按照已收到的 项目", V))
    assert ("2026年饶河县中考考点基本办学条件改善项目", True) in parts

    # 采购人 / 代理机构 values are not underlined
    parts = fill.split_markup(fill.fill_marked("采购人、采购代理机构名称:", V))
    assert all(not underlined for _, underlined in parts)


def test_fill_line_strips_sentinels():
    out = fill.fill_line("（投标人名称： ）", V)
    assert fill.UL_START not in out and fill.UL_END not in out
    assert out == "（投标人名称：示例科技有限公司）"


SUPPLIER_V = {
    "address": "示例市示例路 100 号",
    "postal_code": "000000",
    "phone": "13000000000",
    "email": "test@example.com",
    "bank_name": "示例银行示例支行",
    "bank_account": "0000000000000000000",
    "date": "2026年01月01日",
}


def test_contact_lines():
    values = {**V, **SUPPLIER_V}
    assert fill.fill_line("详细地址:__________ 邮政编码:__________", values) == (
        "详细地址:示例市示例路 100 号\t邮政编码:000000"
    )
    assert fill.fill_line("电 话: __________电子函件:__________", values) == (
        "电话:13000000000\t电子函件:test@example.com"
    )
    assert fill.fill_line("投标人开户银行:__________ 账号/行号:__________", values) == (
        "投标人开户银行:示例银行示例支行\t账号/行号:0000000000000000000"
    )


def test_chop_line():
    values = {**V, **SUPPLIER_V}
    assert fill.fill_line("投标人名称(加盖公章):____________________", values) == (
        "投标人名称（加盖公章）:示例科技有限公司"
    )


def test_date_line():
    values = {**V, **SUPPLIER_V}
    assert fill.fill_line("日 期:____年 ____月 ____日", values) == "日期:2026年01月01日"
    assert fill.fill_line("日期：年月日", values) == "日期:2026年01月01日"
    # an unrelated "截止日期:2025年6月15日" must not be touched
    assert fill.fill_line("投标截止日期:2025年6月15日", values) == "投标截止日期:2025年6月15日"


def test_date_placeholder_is_nbsp_plus_underline():
    nbsp = "\xa0" * 6
    # 纯下划线 → 整段不间断空格
    assert fill.fill_line("日期：____________", V) == "日期:" + nbsp
    # 保留 年/月/日，每个 ____ 替换为不间断空格 + 单下划线
    assert fill.fill_line("日期：____年____月____日", V) == (
        "日期:" + nbsp + "年" + nbsp + "月" + nbsp + "日"
    )
    # 年月日（无下划线）→ 保留占位文字
    assert fill.fill_line("日期：年月日", V) == "日期：年月日"
    # 日期：（无占位）→ 保留原文
    assert fill.fill_line("日期：", V) == "日期："


def test_ph_ul_placeholder_is_nbsp_underline():
    # 占位符（V 不含 address/phone/bank）→ 不间断空格 + 单下划线；真实值 → 普通文本
    nbsp = "\xa0" * 6
    assert fill.fill_line("详细地址:__________ 邮政编码:__________", V) == (
        "详细地址:" + nbsp + "\t邮政编码:" + nbsp
    )
    assert fill.fill_line("电话:__________电子函件:__________", V) == (
        "电话:" + nbsp + "\t电子函件:" + nbsp
    )
    # 值有内容 → 普通文本（无下划线哨兵残留）
    values = {**V, "address": "示例市示例路 100 号"}
    out = fill.fill_line("详细地址:__________ 邮政编码:__________", values)
    assert out == "详细地址:示例市示例路 100 号\t邮政编码:" + nbsp
    assert fill.UL_START not in out and fill.UL_END not in out
