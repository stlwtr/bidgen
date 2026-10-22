import pytest

from bidgen import punctuation


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        # Chinese context: convert
        ("金额3,649,020.00元,共100台.", "金额3,649,020.00元，共100台。"),
        ("屏幕比例16:10,分辨率高.", "屏幕比例16:10，分辨率高。"),
        ("规格8dB(A),符合(Cr)≤20", "规格8dB(A)，符合(Cr)≤20"),
        ("型号(1m,1w),如下:", "型号(1m,1w)，如下："),
        ("本章(如涉及)内容", "本章（如涉及）内容"),
        ("序号一,二;三!", "序号一，二；三！"),
        ("详细地址:__________", "详细地址：__________"),
        # a colon after a Chinese label converts even before digits/letters
        ("电话:13000000000", "电话：13000000000"),
        ("账号/行号:450401", "账号/行号：450401"),
        ("16:10", "16:10"),
        # English / numeric context: keep
        ("This is a test, do not change.", "This is a test, do not change."),
        # Leading punctuation has no Chinese left neighbour: keep
        (",中文开头", ",中文开头"),
        (".中文开头", ".中文开头"),
        # List marker / decimal after a digit keeps its period
        ("1.按照已收到的 项目(项目编号: )招标文件要求,经我方",
         "1.按照已收到的项目（项目编号： ）招标文件要求，经我方"),
        ("12.1投标人应当投标.", "12.1投标人应当投标。"),
        # CJK-adjacent spaces (PDF layout artifacts) are collapsed
        ("采购 人", "采购人"),
        ("章 投 标", "章投标"),
        ("。 递", "。递"),
        ("规格加 (单位)", "规格加（单位）"),
        ("备注: 年内有效", "备注：年内有效"),
        # fill-in blank between two punctuation marks is preserved
        ("（编号： ）", "（编号： ）"),
        # space between closing bracket and sentence mark is removed
        ("（说明） 。", "（说明）。"),
        ("（如有）：__________ 。", "（如有）：__________。"),
        # Chinese <-> ASCII runs stay contiguous (no space between them)
        ("USB 接口", "USB接口"),
        ("第 1 章", "第1章"),
        ("500 万", "500万"),
        ("按 F9 更新", "按F9更新"),
        # ASCII-only pairs keep their space
        ("USB 2.0", "USB 2.0"),
    ],
)
def test_normalize(src, expected):
    assert punctuation.normalize(src) == expected


def test_empty():
    assert punctuation.normalize("") == ""
