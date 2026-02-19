import json
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from .utils import get_llm_response


class ReportGenerator:

    async def generate(self, url: str, metrics: dict) -> str:
        
        # Calculate scores
        scored_metrics = self._calculate_scores(metrics)
        
        # Get LLM analysis
        llm_insights = await self._get_llm_insights(url, scored_metrics)
        
        # Generate PDF
        pdf_path = self._create_pdf(url, scored_metrics, llm_insights)
        
        return pdf_path

    def _calculate_scores(self, metrics: dict) -> dict:

        scored = {}
        
        for dimension, data in metrics.items():
            scored[dimension] = data.copy()
            
            if dimension == "Security":
                # Count positive security features
                positives = sum([
                    data.get('https_tls', False) or False,
                    data.get('x_frame_options', False) or False,
                    data.get('strict_transport_security', False) or False,
                    data.get('csp', False) or False,
                    data.get('x_content_type_options', False) or False,
                    data.get('referrer_policy', False) or False,
                    data.get('permissions_policy', False) or False,
                ])
                negatives = sum([
                    not data.get('cors_misconfig', True) or False,
                    data.get('outdated_js', False) or False,
                ])
                sri = data.get('sri_coverage', [0, 1]) or [0, 1]
                sri_score = sri[0] / sri[1] if sri[1] > 0 else 0
                scored[dimension]['score'] = ((positives + sri_score - negatives) / 8) * 100
                
            elif dimension == "UX & Accessibility":
                issues = len(data.get('accessibility_issues', [])) or []
                deductions = (
                    (5 if data.get('title_too_long', False) else 0) +
                    (10 if data.get('meta_description_missing', False) else 0) +
                    min(data.get('forms_missing_labels', 0) * 2, 20) +
                    min(data.get('images_without_alt', 0) * 1.5, 20) +
                    min(data.get('links_without_text', 0) * 3, 10) +
                    min(issues * 5, 20)
                )
                scored[dimension]['score'] = max(0, 100 - deductions)
                
            elif dimension == "Performance":
                # Score based on thresholds
                page_size = data.get('page_size_bytes', 0) or 0
                ttfb = data.get('ttfb_ms', 0) or 0
                tti = data.get('tti_ms', 0) or 0
                
                size_score = max(0, 100 - (page_size / 10000))  # Deduct for large pages
                ttfb_score = max(0, 100 - (ttfb / 10))  # Good TTFB < 200ms
                tti_score = max(0, 100 - (tti / 50))  # Good TTI < 3000ms
                
                scored[dimension]['score'] = (size_score + ttfb_score + tti_score) / 3
                
            elif dimension == "Technical Quality":
                broken = data.get('broken_links', 0) or 0
                total = data.get('total_links_checked', 1) or 0
                missing_meta = len(data.get('missing_meta_tags', [])) or []
                redirects = data.get('redirect_chain_length', 0) or 0
                
                deductions = (
                    (broken / total * 30 if total > 0 else 0) +
                    (missing_meta * 10) +
                    (redirects * 5)
                )
                scored[dimension]['score'] = max(0, 100 - deductions)
        
        return scored

    async def _get_llm_insights(self, url: str, metrics: dict) -> dict:

        prompt = f"""You are a QA analyst. Analyze these website quality metrics for {url}.

Metrics:
{json.dumps(metrics, indent=2)}

Provide a professional analysis with:
1. Summary: 2-3 sentences about overall quality, highlighting the calculated scores
2. Recommendations: Top 5 specific, actionable improvements based on the actual metrics (mention specific numbers)

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{{
  "summary": "your summary here",
  "recommendations": ["rec 1", "rec 2", "rec 3", "rec 4", "rec 5"]
}}

Do not include any markdown formatting, code blocks, or additional text."""
        
        response = get_llm_response(prompt)
        
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        
        try:
            insights = json.loads(response.strip())
            if 'summary' not in insights or 'recommendations' not in insights:
                raise ValueError("Missing required fields")
        except Exception as e:
            print(f"LLM JSON parsing error: {e}")
            print(f"Response was: {response}")
            insights = {
                "summary": "Unable to generate automated insights. Please review the detailed metrics below.",
                "recommendations": [
                    "Review each dimension score for areas needing improvement",
                    "Focus on dimensions with scores below 70",
                    "Implement security best practices",
                    "Optimize page performance",
                    "Improve accessibility compliance"
                ]
            }
        
        return insights

    def _create_pdf(self, url: str, metrics: dict, insights: dict) -> str:
        
        os.makedirs("reports", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reports/qa_report_{timestamp}.pdf"
        
        doc = SimpleDocTemplate(
            filename, 
            pagesize=letter,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#333333')
        )
        
        story.append(Paragraph("Website Quality Analysis Report", title_style))
        story.append(Paragraph(
            f"{url}<br/>{datetime.now().strftime('%B %d, %Y at %H:%M')}", 
            subtitle_style
        ))
        
        scores = [data.get('score', 0) for data in metrics.values()]
        overall_score = sum(scores) / len(scores) if scores else 0
        
        score_color = self._get_score_color(overall_score)
        
        score_number_style = ParagraphStyle(
            'ScoreNumber',
            parent=styles['Normal'],
            fontSize=36,
            leading=36,         
            spaceBefore=0,       
            spaceAfter=0,        
            alignment=TA_CENTER,
            textColor=colors.white,
            fontName='Helvetica-Bold'
        )

        score_label_style = ParagraphStyle(
            'ScoreLabel',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,          
            spaceBefore=0,       
            spaceAfter=0,        
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1a1a1a')
        )

        score_data = [[
            Paragraph(f'{overall_score:.0f}', score_number_style),
            Paragraph(
                f'<b>Overall Quality Score</b><br/>'
                f'<font color="#666">{self._get_score_label(overall_score)}</font>',
                score_label_style
            )
        ]]

        score_table = Table(
            score_data,
            colWidths=[1.5*inch, 4*inch],
            rowHeights=[0.95*inch]   # << important (tweak 0.85–1.1 if needed)
        )

        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), score_color),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f8f9fa')),

            ('ALIGN',  (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#dee2e6')),

            # Use per-cell padding so the number is truly centered
            ('LEFTPADDING',  (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 0),
            ('TOPPADDING',   (0, 0), (0, 0), 0),
            ('BOTTOMPADDING',(0, 0), (0, 0), 0),

            ('LEFTPADDING',  (1, 0), (1, 0), 15),
            ('RIGHTPADDING', (1, 0), (1, 0), 10),
            ('TOPPADDING',   (1, 0), (1, 0), 12),
            ('BOTTOMPADDING',(1, 0), (1, 0), 12),
        ]))
            
        story.append(score_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(insights.get('summary', 'N/A'), body_style))
        story.append(Spacer(1, 0.3 * inch))
        
        story.append(Paragraph("Quality Dimensions", heading_style))
        story.append(Spacer(1, 0.1 * inch))
        
        dim_data = [['Dimension', 'Score', 'Status']]
        for dimension, data in metrics.items():
            score = data.get('score', 0)
            score_str = f"{score:.1f}/100"
            status = self._get_score_label(score)
            dim_data.append([dimension, score_str, status])
        
        dim_table = Table(dim_data, colWidths=[2.5*inch, 1.5*inch, 2*inch])
        dim_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(dim_table)
        story.append(Spacer(1, 0.4 * inch))
        
        story.append(Paragraph("Detailed Metrics", heading_style))
        story.append(Spacer(1, 0.15 * inch))
        
        detail_key_style = ParagraphStyle(
            'DetailKey',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            fontName='Helvetica-Bold'
        )
        
        detail_value_style = ParagraphStyle(
            'DetailValue',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            leading=12
        )
        
        for dimension, data in metrics.items():
            dim_header_style = ParagraphStyle(
                'DimHeader',
                parent=styles['Heading3'],
                fontSize=13,
                textColor=colors.HexColor('#2C3E50'),
                spaceAfter=8,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(f"{dimension} ({data.get('score', 0):.1f}/100)", dim_header_style))
            
            detail_data = []
            for key, value in data.items():
                if key == 'score':
                    continue
                    
                if isinstance(value, bool):
                    value_str = "✓ Yes" if value else "✗ No"
                elif isinstance(value, list):
                    if len(value) == 2 and all(isinstance(x, (int, float)) for x in value):
                        value_str = f"{value[0]} of {value[1]}"
                    elif value:
                        value_str = ", ".join(str(v) for v in value)
                    else:
                        value_str = "None"
                elif isinstance(value, (int, float)):
                    value_str = f"{value:,.0f}" if isinstance(value, int) or value.is_integer() else f"{value:,.2f}"
                else:
                    value_str = str(value) if value else "None"
                
                key_formatted = key.replace('_', ' ').title()
                
                detail_data.append([
                    Paragraph(key_formatted, detail_key_style),
                    Paragraph(value_str, detail_value_style)
                ])
            
            if detail_data:
                detail_table = Table(detail_data, colWidths=[2.5*inch, 3.5*inch])
                detail_table.setStyle(TableStyle([
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(detail_table)
            story.append(Spacer(1, 0.2 * inch))
        
        story.append(Paragraph("Recommendations for Improvement", heading_style))
        story.append(Spacer(1, 0.1 * inch))
        
        for i, rec in enumerate(insights.get('recommendations', []), 1):
            rec_style = ParagraphStyle(
                'Rec',
                parent=body_style,
                leftIndent=20,
                bulletIndent=10,
                spaceAfter=8
            )
            story.append(Paragraph(f"{i}. {rec}", rec_style))
        
        doc.build(story)
        
        return filename
    
    def _get_score_color(self, score: float) -> colors.Color:

        if score >= 80:
            return colors.HexColor('#28a745')  
        elif score >= 60:
            return colors.HexColor('#ffc107')  
        elif score >= 40:
            return colors.HexColor('#fd7e14')  
        else:
            return colors.HexColor('#dc3545')  
    
    def _get_score_label(self, score: float) -> str:

        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Needs Improvement"
        else:
            return "Critical Issues"
