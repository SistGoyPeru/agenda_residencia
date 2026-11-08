import pathlib
p=pathlib.Path(r"C:\Users\alexg\OneDrive\Alex_2026\AGENDA PARA TRASNPORTITAS DE REPARTOS\residencias\views.py")
s=p.read_text(encoding="utf-8")

old='''    elementos.append(Paragraph("Detalle de entregas", seccion))
    if datos["filas"]:
        filas = [
            [
                Paragraph("Fecha", cabecera_celda),
                Paragraph("Residencia", cabecera_celda),
                Paragraph("Turno", cabecera_celda),
                Paragraph("Productos", cabecera_celda),
                Paragraph("Unid.", cabecera_celda),
                Paragraph("Cup.", cabecera_celda),
            ]
        ]
        for fila in datos["filas"]:
            visita = fila["visita"]
            productos = ", ".join(
                f"{linea.cantidad}Ã— {linea.producto.nombre}"
                for linea in visita.lineas.all()
            )
            filas.append(
                [
                    Paragraph(f"{visita.fecha:%d/%m/%Y}", celda),
                    Paragraph(visita.residencia.nombre, celda),
                    Paragraph(visita.get_turno_display(), celda),
                    Paragraph(productos or "â€”", celda),
                    Paragraph(str(fila["unidades"]), celda),
                    Paragraph(str(fila["cupones"]), celda),
                ]
            )
        filas.append(
            [
                Paragraph("Totales", celda),
                Paragraph("", celda),
                Paragraph("", celda),
                Paragraph("", celda),
                Paragraph(str(datos["total_unidades"]), celda),
                Paragraph(str(datos["total_cupones"]), celda),
            ]
        )
        tabla = Table(
            filas,
            colWidths=[1.7 * cm, 4.1 * cm, 1.7 * cm, 5.7 * cm, 1.3 * cm, 1.3 * cm],
            repeatRows=1,
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (4, 1), (5, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d7e3e0")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elementos.append(tabla)
    else:
        elementos.append(
            Paragraph("No hay entregas registradas en este periodo.", subtitulo)
        )

'''
new='''
'''
if old in s:
    s=s.replace(old,new,1)
    p.write_text(s,encoding="utf-8")
    print("ok eliminado detalle entregas")
else:
    print("NO MATCH")
    import re
    m=re.search(r"elementos\.append\(Paragraph\(\"Detalle de entregas\"", s)
    print("Encontrado en:", m.start() if m else None)
