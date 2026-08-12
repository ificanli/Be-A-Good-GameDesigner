"""按白名单构建 GitHub Pages 公开内容。

内部规范、待判断、来源登记、OCR、原始资料和工具不会复制到 docs。
运行：python scripts/build_public_site.py
"""

from pathlib import Path
import os
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.html"

PUBLIC_ARTICLES = (
    "05_数值与经济/游戏数值设计方法/数值建模-从体验目标到标准模型.md",
    "05_数值与经济/游戏数值设计方法/属性体系设计-从定义转化到系统投放.md",
    "05_数值与经济/游戏数值设计方法/伤害流程设计-从命中判定到最终结算.md",
    "05_数值与经济/游戏数值设计方法/输出循环与TTK验证.md",
    "05_数值与经济/游戏数值设计方法/等级与经验设计-从成长时间表到进度追赶.md",
    "05_数值与经济/游戏数值设计方法/玩家成长与内容梯度设计.md",
    "05_数值与经济/游戏数值设计方法/养成系统规划-从总强度预算到模块投放.md",
    "05_数值与经济/游戏数值设计方法/装备系统设计-从模块预算到掉落养成与替换.md",
    "05_数值与经济/游戏数值设计方法/技能与天赋设计-从技能模板到循环养成与构筑验证.md",
    "05_数值与经济/游戏数值设计方法/资源经济设计-从养成需求到产出消耗复盘.md",
    "05_数值与经济/游戏数值设计方法/多货币体系设计-职责兑换套利与认知成本.md",
    "05_数值与经济/游戏数值设计方法/随机掉落设计-累计概率保底与收集周期.md",
)


def main():
    if not INDEX.exists():
        raise FileNotFoundError("docs/index.html 不存在，无法保留网站外壳")

    allowed = {Path(article) for article in PUBLIC_ARTICLES}
    allowed.add(Path("index.html"))

    for path in sorted(DOCS.rglob("*"), reverse=True):
        if path.is_file() and path.relative_to(DOCS) not in allowed:
            path.unlink()
    for path in sorted(DOCS.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    public_paths = {Path(article) for article in PUBLIC_ARTICLES}

    def render_public_copy(article):
        source = ROOT / article
        text = source.read_text(encoding="utf-8")

        def replace_wiki_link(match):
            raw_target = match.group(1)
            label = match.group(2) or Path(raw_target).name
            resolved = (Path(article).parent / raw_target).with_suffix(".md")
            normalized = Path(os.path.normpath(resolved.as_posix()))
            if normalized not in public_paths:
                return label
            relative = os.path.relpath(normalized, Path(article).parent).replace("\\", "/")
            return f"[{label}]({relative})"

        return re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", replace_wiki_link, text)

    for article in PUBLIC_ARTICLES:
        source = ROOT / article
        target = DOCS / article
        if not source.exists():
            raise FileNotFoundError(f"公开白名单文件不存在：{article}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_public_copy(article), encoding="utf-8")

    print("公开文章：")
    for article in PUBLIC_ARTICLES:
        print(f"- {article}")


if __name__ == "__main__":
    main()
