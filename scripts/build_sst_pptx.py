#!/usr/bin/env python3
from __future__ import annotations

import os
import zipfile
from xml.sax.saxutils import escape


OUT_DIR = "/data4/jjgong/codegen_sstnoc/docs"
OUT_FILE = os.path.join(OUT_DIR, "sst-codegen-tech-route.pptx")


def content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>OpenAI Codex</Application>
  <Slides>1</Slides>
  <Notes>0</Notes>
  <HiddenSlides>0</HiddenSlides>
  <MMClips>0</MMClips>
  <PresentationFormat>Widescreen</PresentationFormat>
</Properties>
"""


def core_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>SST 首版 Codegen 技术路线</dc:title>
  <dc:creator>OpenAI Codex</dc:creator>
  <cp:lastModifiedBy>OpenAI Codex</cp:lastModifiedBy>
</cp:coreProperties>
"""


def presentation_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
 slideSizeCx="12192000" slideSizeCy="6858000" notesSizeCx="6858000" notesSizeCy="9144000">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId2"/>
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"""


def presentation_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>
"""


def slide_master_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld name="Master">
    <p:bg>
      <p:bgPr>
        <a:solidFill><a:srgbClr val="F7F1E8"/></a:solidFill>
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="1" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle/>
    <p:bodyStyle/>
    <p:otherStyle/>
  </p:txStyles>
</p:sldMaster>
"""


def slide_master_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""


def slide_layout_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"""


def slide_layout_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""


def theme_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Codex Theme">
  <a:themeElements>
    <a:clrScheme name="Codex">
      <a:dk1><a:srgbClr val="1B1B1B"/></a:dk1>
      <a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="4F5B66"/></a:dk2>
      <a:lt2><a:srgbClr val="F7F1E8"/></a:lt2>
      <a:accent1><a:srgbClr val="C76B3A"/></a:accent1>
      <a:accent2><a:srgbClr val="A24A2A"/></a:accent2>
      <a:accent3><a:srgbClr val="B9A48B"/></a:accent3>
      <a:accent4><a:srgbClr val="6C7A89"/></a:accent4>
      <a:accent5><a:srgbClr val="8C9B6E"/></a:accent5>
      <a:accent6><a:srgbClr val="B75E5E"/></a:accent6>
      <a:hlink><a:srgbClr val="0563C1"/></a:hlink>
      <a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Codex">
      <a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont>
      <a:minorFont><a:latin typeface="Aptos"/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Codex">
      <a:fillStyleLst><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:fillStyleLst>
      <a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln></a:lnStyleLst>
      <a:effectStyleLst><a:effectStyle/></a:effectStyleLst>
      <a:bgFillStyleLst><a:solidFill><a:schemeClr val="lt2"/></a:solidFill></a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/>
  <a:extraClrSchemeLst/>
</a:theme>
"""


def slide_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""


def textbox(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, paragraphs: list[tuple[str, int, str, bool]]) -> str:
    ps = []
    for text, size, color, bold in paragraphs:
        rpr = f'<a:rPr lang="zh-CN" sz="{size}" b="{"1" if bold else "0"}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:rPr>'
        ps.append(f'<a:p><a:r>{rpr}<a:t>{escape(text)}</a:t></a:r></a:p>')
    joined = "".join(ps)
    return f"""<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{shape_id}" name="{escape(name)}"/>
    <p:cNvSpPr txBox="1"/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="91440" tIns="45720" rIns="91440" bIns="45720"/>
    <a:lstStyle/>
    {joined}
  </p:txBody>
</p:sp>"""


def rounded_box(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, fill: str, line: str, paragraphs: list[tuple[str, int, str, bool]]) -> str:
    ps = []
    for text, size, color, bold in paragraphs:
        rpr = f'<a:rPr lang="zh-CN" sz="{size}" b="{"1" if bold else "0"}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:rPr>'
        ps.append(f'<a:p><a:r>{rpr}<a:t>{escape(text)}</a:t></a:r></a:p>')
    joined = "".join(ps)
    return f"""<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{shape_id}" name="{escape(name)}"/>
    <p:cNvSpPr/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="137160" tIns="91440" rIns="137160" bIns="91440"/>
    <a:lstStyle/>
    {joined}
  </p:txBody>
</p:sp>"""


def arrow(shape_id: int, name: str, x: int, y: int, cx: int, cy: int) -> str:
    return f"""<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{shape_id}" name="{escape(name)}"/>
    <p:cNvSpPr/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
    <a:prstGeom prst="chevron"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="C76B3A"/></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
</p:sp>"""


def slide_xml() -> str:
    shapes = []
    shapes.append(textbox(2, "Title", 480000, 260000, 11000000, 700000, [
        ("SST 首版 Codegen 技术路线", 2600, "1B1B1B", True),
    ]))
    shapes.append(textbox(3, "Subtitle", 520000, 950000, 10800000, 450000, [
        ("目标：仅修改 tilelang，在识别 SST 后端目标后生成包含 RISC-V 自定义指令痕迹的 C 代码", 1150, "4F5B66", False),
    ]))

    shapes.append(rounded_box(4, "Box1", 430000, 1450000, 2700000, 3450000, "FFFDF8", "B9A48B", [
        ("1. 输入与目标标准化", 1500, "A24A2A", True),
        ("• 用户侧 target 采用 “c + SST 标记”", 1180, "222222", False),
        ("• 不引入新的 target kind", 1180, "222222", False),
        ("• 在 target.py 中统一标准化", 1180, "222222", False),
        ("• 新增 normalize_sst_target / is_sst_target", 1180, "222222", False),
        ("• 保持 target.kind.name == \"c\"", 1180, "222222", False),
    ]))
    shapes.append(rounded_box(5, "Box2", 3550000, 1450000, 3600000, 3450000, "FFFDF8", "B9A48B", [
        ("2. 复用 tilelang 现有编译链", 1500, "A24A2A", True),
        ("• lower.py 继续走现有 C backend", 1180, "222222", False),
        ("• 设备侧入口：target.build.tilelang_c", 1180, "222222", False),
        ("• 核心落点：CodeGenTileLangC", 1180, "222222", False),
        ("• 关键改动：VisitExpr_(CallNode)", 1180, "222222", False),
        ("• 识别 call_extern(\"tl.sst.xxx\", ...)", 1180, "222222", False),
    ]))
    shapes.append(rounded_box(6, "Box3", 7600000, 1450000, 3600000, 3450000, "FFF2E8", "C76B3A", [
        ("3. SST 指令承载与验证", 1500, "A24A2A", True),
        ("• 首版不直接生成复杂 inline asm", 1180, "222222", False),
        ("• 先输出宏/内联函数形式的 C 代码", 1180, "222222", False),
        ("• 示例：SST_RISCV_CUSTOM_OP(...)", 1180, "222222", False),
        ("• 测试重点：校验生成源码字符串", 1180, "222222", False),
        ("• TileOPs 当前只作为 GEMM 联调参考", 1180, "222222", False),
    ]))
    shapes.append(arrow(7, "Arrow1", 3150000, 2850000, 250000, 320000))
    shapes.append(arrow(8, "Arrow2", 7200000, 2850000, 250000, 320000))
    shapes.append(textbox(9, "Bottom", 520000, 5600000, 10800000, 500000, [
        ("实施顺序：target 标准化 → SST 判断辅助函数 → C backend 分支输出 → 最小 codegen 字符串测试 → 后续接入 TileOPs GEMM 用例联调", 1120, "222222", False),
    ]))

    shape_xml = "".join(shapes)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg>
      <p:bgPr>
        <a:solidFill><a:srgbClr val="F7F1E8"/></a:solidFill>
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {shape_xml}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def build_pptx(out_file: str) -> None:
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types())
        zf.writestr("_rels/.rels", root_rels())
        zf.writestr("docProps/app.xml", app_xml())
        zf.writestr("docProps/core.xml", core_xml())
        zf.writestr("ppt/presentation.xml", presentation_xml())
        zf.writestr("ppt/_rels/presentation.xml.rels", presentation_rels())
        zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels())
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels())
        zf.writestr("ppt/theme/theme1.xml", theme_xml())
        zf.writestr("ppt/slides/slide1.xml", slide_xml())
        zf.writestr("ppt/slides/_rels/slide1.xml.rels", slide_rels())


if __name__ == "__main__":
    build_pptx(OUT_FILE)
    print(OUT_FILE)
