from fpdf import FPDF
from datetime import datetime

class IntelligenceReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Omnisight Intelligence Report', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_pdf(title, data):
    """
    Highly robust PDF generator using safe lookups.
    """
    try:
        pdf = IntelligenceReport()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Heading
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, f"{title}", 0, 1)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        # Data Loop
        items = data if isinstance(data, list) else [data]
        
        for item in items:
            if not isinstance(item, dict):
                continue

            # Try to identify if it's an Intelligence Event (has source or sentiment info)
            is_event = False
            # Various possible keys for source and sentiment
            src_val = item.get('source') or item.get('source_type') or item.get('Source')
            sent_val = item.get('sentiment') or item.get('sentiment_score') or item.get('Sentiment')
            
            # If it's an event, we format it as a block
            if src_val or sent_val:
                pdf.set_x(10)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.multi_cell(0, 10, f"Source: {src_val} | Sentiment: {sent_val}")
                pdf.set_font('Helvetica', '', 11)
                content = item.get('content') or item.get('summary') or item.get('Text') or ""
                # Strip special characters to help fpdf encoding
                content_safe = "".join(i for i in str(content) if ord(i) < 128)
                pdf.set_x(10)
                pdf.multi_cell(0, 8, content_safe)
                pdf.ln(5)
            else:
                # Manual KV dump for correlation/summaries
                for k, v in item.items():
                    k_str = str(k).replace('_', ' ').capitalize()
                    v_str = str(v)
                    # Safe ASCII conversion
                    k_safe = "".join(i for i in k_str if ord(i) < 128)
                    v_safe = "".join(i for i in v_str if ord(i) < 128)
                    
                    pdf.set_x(10)
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(0, 8, f"{k_safe}:", 0, 1)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.set_x(10)
                    import textwrap
                    wrapped_v = "\n".join(textwrap.wrap(v_safe, width=90))
                    pdf.multi_cell(0, 8, f"{wrapped_v}")
                pdf.ln(5)

        # Output logic (handles fpdf1 vs fpdf2)
        out = pdf.output(dest='S')
        if isinstance(out, str):
            return out.encode('latin-1', 'ignore')
        return bytes(out) if isinstance(out, bytearray) else out
        
    except Exception as e:
        # Final emergency fallback: Create a minimal error PDF
        err_pdf = FPDF()
        err_pdf.add_page()
        err_pdf.set_font('Helvetica', 'B', 12)
        err_pdf.cell(0, 10, f"PDF Generation Error: {str(e)}", 0, 1)
        out = err_pdf.output(dest='S')
        if isinstance(out, str):
            return out.encode('latin-1', 'ignore')
        return bytes(out) if isinstance(out, bytearray) else out


