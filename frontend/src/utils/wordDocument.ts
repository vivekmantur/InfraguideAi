import type { Assessment } from "../types";
import cognineLogoUrl from "../static/image (7).png";
import { formatMoney, list } from "./format";

const XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
const WORD_NS =
  'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' +
  'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ' +
  'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" ' +
  'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" ' +
  'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"';

type ZipEntry = {
  path: string;
  bytes: Uint8Array;
};

export async function downloadAssessmentWordDocument(assessment: Assessment) {
  const logoBytes = await imageUrlToBytes(cognineLogoUrl);
  const docxBytes = buildDocx(assessment, logoBytes);
  const blob = new Blob([docxBytes], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "infraguide-ai-migration-blueprint.docx";
  anchor.click();
  URL.revokeObjectURL(url);
}

async function imageUrlToBytes(url: string) {
  const response = await fetch(url);
  return new Uint8Array(await response.arrayBuffer());
}

function buildDocx(assessment: Assessment, logoBytes: Uint8Array) {
  const entries: ZipEntry[] = [
    textEntry("[Content_Types].xml", contentTypesXml()),
    textEntry("_rels/.rels", packageRelationshipsXml()),
    textEntry("word/document.xml", documentXml(assessment)),
    textEntry("word/styles.xml", stylesXml()),
    textEntry("word/_rels/document.xml.rels", documentRelationshipsXml()),
    textEntry("word/header1.xml", headerXml()),
    textEntry("word/_rels/header1.xml.rels", headerRelationshipsXml()),
    textEntry("word/footer1.xml", footerXml()),
    { path: "word/media/cognine.png", bytes: logoBytes },
  ];

  return createZip(entries);
}

function contentTypesXml() {
  return `${XML_DECLARATION}
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>`;
}

function packageRelationshipsXml() {
  return `${XML_DECLARATION}
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`;
}

function documentRelationshipsXml() {
  return `${XML_DECLARATION}
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
  <Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>`;
}

function headerRelationshipsXml() {
  return `${XML_DECLARATION}
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdLogo" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/cognine.png"/>
</Relationships>`;
}

function headerXml() {
  return `${XML_DECLARATION}
<w:hdr ${WORD_NS}>
  <w:tbl>
    <w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders><w:bottom w:val="single" w:sz="4" w:space="0" w:color="CFD8D3"/></w:tblBorders></w:tblPr>
    <w:tblGrid><w:gridCol w:w="7200"/><w:gridCol w:w="2160"/></w:tblGrid>
    <w:tr>
      <w:tc>
        <w:tcPr><w:tcW w:w="7200" w:type="dxa"/><w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders></w:tcPr>
        ${paragraph("InfraGuide AI Migration Blueprint", { bold: true, color: "2F5D50", size: 18 })}
      </w:tc>
      <w:tc>
        <w:tcPr><w:tcW w:w="2160" w:type="dxa"/><w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders></w:tcPr>
        ${imageParagraph()}
      </w:tc>
    </w:tr>
  </w:tbl>
</w:hdr>`;
}

function footerXml() {
  return `${XML_DECLARATION}
<w:ftr ${WORD_NS}>
  <w:tbl>
    <w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="CFD8D3"/></w:tblBorders></w:tblPr>
    <w:tblGrid><w:gridCol w:w="7200"/><w:gridCol w:w="2160"/></w:tblGrid>
    <w:tr>
      <w:tc>
        <w:tcPr><w:tcW w:w="7200" w:type="dxa"/><w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders></w:tcPr>
        ${paragraph(`Copyright (c) ${new Date().getFullYear()} Cognine. All rights reserved.`, { color: "6A756F", size: 17 })}
      </w:tc>
      <w:tc>
        <w:tcPr><w:tcW w:w="2160" w:type="dxa"/><w:tcBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders></w:tcPr>
        ${paragraph("Confidential", { color: "6A756F", size: 17, align: "right" })}
      </w:tc>
    </w:tr>
  </w:tbl>
</w:ftr>`;
}

function documentXml(assessment: Assessment) {
  const stack = assessment.technology_stack;
  const cost = assessment.cost_estimation;
  const governance = assessment.governance_assessment ?? {
    risk_level: "Not assessed",
    issues: [],
    passed_checks: [],
    recommendations: [],
    recommendation: "Security and governance assessment was not returned by the API.",
  };

  return `${XML_DECLARATION}
<w:document ${WORD_NS}>
  <w:body>
    ${paragraph("InfraGuide AI Migration Blueprint", { style: "Title" })}
    ${paragraph("Generated migration assessment and cloud modernization plan.", { color: "4F5F57" })}
    ${heading("Assessment Summary", 1)}
    ${table([
      ["Architecture Summary", assessment.architecture_summary],
      ["Recommended Provider", assessment.recommended_provider],
      ["Migration Strategy", assessment.migration_strategy],
      ["Readiness Score", `${assessment.cloud_readiness.score}%`],
    ])}
    ${heading("1. Technology Stack", 1)}
    ${table([
      ["Languages", list(stack.languages)],
      ["Frameworks", list(stack.frameworks)],
      ["Runtime", list(stack.runtimes)],
      ["Hosting Model", stack.hosting_model ?? "Not detected"],
      ["Deployment Model", stack.deployment_model ?? "Not detected"],
      ["Triggers", list(stack.triggers)],
      ["Databases", list(stack.databases)],
      ["Package Managers", list(stack.package_managers)],
      ["Container Configurations", list(stack.container_configs)],
      ["Cloud Dependencies", list(stack.cloud_dependencies)],
    ])}
    ${heading("2. Cloud Readiness", 1)}
    ${table([
      ["Score", `${assessment.cloud_readiness.score}%`],
      ["Complexity", assessment.cloud_readiness.complexity],
      ["Runtime Compatibility", assessment.cloud_readiness.runtime_compatibility],
      ["Database Compatibility", assessment.cloud_readiness.database_compatibility],
      ["Container Readiness", assessment.cloud_readiness.container_readiness],
      ["Configuration Readiness", assessment.cloud_readiness.configuration_readiness],
    ])}
    ${heading("Score Breakdown", 2)}
    ${listParagraphs(assessment.cloud_readiness.score_breakdown)}
    ${heading("3. Recommended Cloud Services", 1)}
    ${table([["Component", "Current State", "Recommended Service"], ...assessment.recommended_services.map((service) => [service.component, service.current, service.recommended])], true)}
    ${heading("4. Cost Estimate", 1)}
    ${table([
      ["Currency", cost.currency],
      ["Monthly Cost", formatMoney(cost.currency, cost.monthly)],
      ["Monthly Range", cost.monthly_range ?? "Not estimated"],
      ["Annual Cost", formatMoney(cost.currency, cost.annual)],
    ])}
    ${heading("Line Items", 2)}
    ${listParagraphs(cost.line_items)}
    ${heading("Assumptions", 2)}
    ${listParagraphs(cost.assumptions)}
    ${heading("5. Dependencies", 1)}
    ${listParagraphs(stack.dependency_graph)}
    ${heading("6. Security And Governance", 1)}
    ${table([
      ["Risk Level", governance.risk_level],
      ["Recommendation", governance.recommendation],
    ])}
    ${heading("Passed Checks", 2)}
    ${listParagraphs(governance.passed_checks)}
    ${heading("Issues", 2)}
    ${listParagraphs(governance.issues)}
    ${heading("Recommendations", 2)}
    ${listParagraphs(governance.recommendations)}
    ${heading("7. Modernization Opportunities", 1)}
    ${listParagraphs(assessment.modernization_opportunities)}
    ${heading("8. Migration Roadmap", 1)}
    ${listParagraphs(assessment.migration_roadmap, true)}
    ${assessment.warnings.length > 0 ? `${heading("9. Warnings", 1)}${listParagraphs(assessment.warnings)}` : ""}
    <w:sectPr>
      <w:headerReference w:type="default" r:id="rIdHeader"/>
      <w:footerReference w:type="default" r:id="rIdFooter"/>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1296" w:right="1008" w:bottom="1008" w:left="1008" w:header="540" w:footer="540" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>`;
}

function stylesXml() {
  return `${XML_DECLARATION}
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="17201B"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr><w:b/><w:color w:val="2F5D50"/><w:sz w:val="48"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:rPr><w:b/><w:color w:val="2F5D50"/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:rPr><w:b/><w:color w:val="17201B"/><w:sz w:val="26"/></w:rPr>
  </w:style>
</w:styles>`;
}

function heading(text: string, level: 1 | 2) {
  return paragraph(text, { style: level === 1 ? "Heading1" : "Heading2", spacingBefore: level === 1 ? 360 : 240, spacingAfter: 120 });
}

function paragraph(
  text: string,
  options: {
    style?: string;
    bold?: boolean;
    color?: string;
    size?: number;
    align?: "left" | "right" | "center";
    spacingBefore?: number;
    spacingAfter?: number;
  } = {},
) {
  const props = [
    options.style ? `<w:pStyle w:val="${options.style}"/>` : "",
    options.align ? `<w:jc w:val="${options.align}"/>` : "",
    options.spacingBefore || options.spacingAfter ? `<w:spacing w:before="${options.spacingBefore ?? 0}" w:after="${options.spacingAfter ?? 120}"/>` : `<w:spacing w:after="120"/>`,
  ].join("");
  const runProps = [
    options.bold ? "<w:b/>" : "",
    options.color ? `<w:color w:val="${options.color}"/>` : "",
    options.size ? `<w:sz w:val="${options.size}"/>` : "",
  ].join("");

  return `<w:p><w:pPr>${props}</w:pPr><w:r><w:rPr>${runProps}</w:rPr><w:t xml:space="preserve">${xmlEscape(text)}</w:t></w:r></w:p>`;
}

function listParagraphs(items: string[] | undefined, numbered = false) {
  if (!items?.length) {
    return paragraph("None");
  }

  return items.map((item, index) => paragraph(`${numbered ? `${index + 1}. ` : "- "}${item}`)).join("");
}

function table(rows: string[][], firstRowHeader = false) {
  return `<w:tbl>
    <w:tblPr>
      <w:tblW w:w="0" w:type="auto"/>
      <w:tblBorders>
        <w:top w:val="single" w:sz="4" w:color="CFD8D3"/>
        <w:left w:val="single" w:sz="4" w:color="CFD8D3"/>
        <w:bottom w:val="single" w:sz="4" w:color="CFD8D3"/>
        <w:right w:val="single" w:sz="4" w:color="CFD8D3"/>
        <w:insideH w:val="single" w:sz="4" w:color="CFD8D3"/>
        <w:insideV w:val="single" w:sz="4" w:color="CFD8D3"/>
      </w:tblBorders>
    </w:tblPr>
    ${rows
      .map((row, rowIndex) => `<w:tr>${row.map((cell) => tableCell(cell, firstRowHeader && rowIndex === 0)).join("")}</w:tr>`)
      .join("")}
  </w:tbl>`;
}

function tableCell(text: string, isHeader: boolean) {
  return `<w:tc>
    <w:tcPr>
      <w:tcW w:w="3000" w:type="dxa"/>
      ${isHeader ? '<w:shd w:fill="EEF2EF"/>' : ""}
    </w:tcPr>
    ${paragraph(text, { bold: isHeader })}
  </w:tc>`;
}

function imageParagraph() {
  const width = 914400;
  const height = 241173;

  return `<w:p>
    <w:pPr><w:jc w:val="right"/></w:pPr>
    <w:r>
      <w:drawing>
        <wp:inline distT="0" distB="0" distL="0" distR="0">
          <wp:extent cx="${width}" cy="${height}"/>
          <wp:docPr id="1" name="Cognine Logo"/>
          <a:graphic>
            <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <pic:pic>
                <pic:nvPicPr><pic:cNvPr id="1" name="cognine.png"/><pic:cNvPicPr/></pic:nvPicPr>
                <pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
                <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${width}" cy="${height}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
              </pic:pic>
            </a:graphicData>
          </a:graphic>
        </wp:inline>
      </w:drawing>
    </w:r>
  </w:p>`;
}

function textEntry(path: string, text: string): ZipEntry {
  return { path, bytes: new TextEncoder().encode(text) };
}

function createZip(entries: ZipEntry[]) {
  const fileRecords: Uint8Array[] = [];
  const centralRecords: Uint8Array[] = [];
  let offset = 0;

  for (const entry of entries) {
    const name = new TextEncoder().encode(entry.path);
    const crc = crc32(entry.bytes);
    const localHeader = concatBytes([
      uint32(0x04034b50),
      uint16(20),
      uint16(0),
      uint16(0),
      uint16(0),
      uint16(0),
      uint32(crc),
      uint32(entry.bytes.length),
      uint32(entry.bytes.length),
      uint16(name.length),
      uint16(0),
      name,
    ]);
    const fileRecord = concatBytes([localHeader, entry.bytes]);
    fileRecords.push(fileRecord);

    centralRecords.push(
      concatBytes([
        uint32(0x02014b50),
        uint16(20),
        uint16(20),
        uint16(0),
        uint16(0),
        uint16(0),
        uint16(0),
        uint32(crc),
        uint32(entry.bytes.length),
        uint32(entry.bytes.length),
        uint16(name.length),
        uint16(0),
        uint16(0),
        uint16(0),
        uint16(0),
        uint32(0),
        uint32(offset),
        name,
      ]),
    );
    offset += fileRecord.length;
  }

  const centralDirectory = concatBytes(centralRecords);
  const endRecord = concatBytes([
    uint32(0x06054b50),
    uint16(0),
    uint16(0),
    uint16(entries.length),
    uint16(entries.length),
    uint32(centralDirectory.length),
    uint32(offset),
    uint16(0),
  ]);

  return concatBytes([...fileRecords, centralDirectory, endRecord]);
}

function uint16(value: number) {
  const bytes = new Uint8Array(2);
  const view = new DataView(bytes.buffer);
  view.setUint16(0, value, true);
  return bytes;
}

function uint32(value: number) {
  const bytes = new Uint8Array(4);
  const view = new DataView(bytes.buffer);
  view.setUint32(0, value >>> 0, true);
  return bytes;
}

function concatBytes(chunks: Uint8Array[]) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;

  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.length;
  }

  return output;
}

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff;

  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }

  return (crc ^ 0xffffffff) >>> 0;
}

function xmlEscape(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
