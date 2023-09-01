from pypdf import PdfReader, PdfWriter

pdf_file_in = "docs\datdz0pms85gbnqy4j3k.pdf"
pdf_file_out = "docs\soccer-rules.pdf"
page_start = 8
page_end = 141

pdf = PdfReader(pdf_file_in)

writer = PdfWriter()
for page_num in range(page_start-1, page_end):
    writer.add_page(pdf.pages[page_num])

with open(pdf_file_out, 'wb') as output_file:
    writer.write(output_file)
