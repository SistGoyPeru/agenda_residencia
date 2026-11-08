from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    MovimientoCupon,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
    Zona,
    rango_semana,
    siguiente_residencia,
)
from .views import pendientes_de_la_semana, resumen_semana, estado_plan


def crear_usuario(username="tester"):
    return get_user_model().objects.create_user(username=username, password="Clave1234!")


class CuponesTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("cupones_tester")
        self.producto = Producto.objects.create(
            nombre="Pañales talla M",
            cupones_por_unidad=1,
            stock_minimo=3,
            propietario=self.usuario,
        )
        self.residencia = Residencia.objects.create(
            nombre="Residencia Test", propietario=self.usuario
        )

    def test_stock_descuenta_solo_visitas_entregadas(self):
        MovimientoCupon.objects.create(producto=self.producto, cantidad=10)
        entregada = Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate(),
            turno=Visita.Turno.MANANA,
            estado=Visita.Estado.ENTREGADA,
        )
        VisitaProducto.objects.create(
            visita=entregada, producto=self.producto, cantidad=2, cupones=2
        )
        pendiente = Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate() + timedelta(days=1),
            turno=Visita.Turno.MANANA,
            estado=Visita.Estado.PENDIENTE,
        )
        VisitaProducto.objects.create(
            visita=pendiente, producto=self.producto, cantidad=5, cupones=5
        )
        self.assertEqual(self.producto.stock_actual(), 8)

    def test_cupones_automaticos_al_guardar_linea(self):
        producto = Producto.objects.create(
            nombre="Toallitas", cupones_por_unidad=2, propietario=self.usuario
        )
        visita = Visita.objects.create(
            residencia=self.residencia, fecha=timezone.localdate()
        )
        linea = VisitaProducto.objects.create(
            visita=visita, producto=producto, cantidad=3
        )
        self.assertEqual(linea.cupones, 6)

    def test_borrar_visita_devuelve_cupones(self):
        MovimientoCupon.objects.create(producto=self.producto, cantidad=10)
        visita = Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate(),
            estado=Visita.Estado.ENTREGADA,
        )
        VisitaProducto.objects.create(
            visita=visita, producto=self.producto, cantidad=4, cupones=4
        )
        self.assertEqual(self.producto.stock_actual(), 6)
        visita.delete()
        self.assertEqual(self.producto.stock_actual(), 10)


class SiguienteResidenciaTests(TestCase):
    def test_prioriza_visita_pendiente_de_hoy(self):
        usuario = crear_usuario("siguiente_tester")
        zona = Zona.objects.create(nombre="Centro", propietario=usuario)
        residencia = Residencia.objects.create(
            nombre="San José", zona=zona, propietario=usuario
        )
        Visita.objects.create(
            residencia=residencia,
            fecha=timezone.localdate(),
            turno=Visita.Turno.MANANA,
        )
        resultado = siguiente_residencia(usuario)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["residencia"], residencia)
        self.assertIsNotNone(resultado["visita"])


class SemanaSinDiasFijosTests(TestCase):
    def setUp(self):
        self.hoy = timezone.localdate()
        self.usuario = crear_usuario("semana_tester")
        self.residencia = Residencia.objects.create(
            nombre="San José",
            frecuencia_semanal=1,
            propietario=self.usuario,
        )
        inicio, _ = rango_semana(self.hoy)
        self.otro_dia = inicio + timedelta(days=(self.hoy.weekday() + 1) % 7)

    def test_visita_entregada_cubre_la_semana(self):
        Visita.objects.create(
            residencia=self.residencia,
            fecha=self.hoy,
            estado=Visita.Estado.ENTREGADA,
        )
        self.assertEqual(pendientes_de_la_semana(self.usuario, self.hoy), [])
        resumen = resumen_semana(self.usuario, self.hoy)
        self.assertEqual(resumen["hechas"], 1)
        self.assertEqual(resumen["previstas"], 1)

    def test_visita_programada_no_se_pide_otra_vez(self):
        Visita.objects.create(
            residencia=self.residencia,
            fecha=self.otro_dia,
            estado=Visita.Estado.PENDIENTE,
        )
        self.assertEqual(pendientes_de_la_semana(self.usuario, self.hoy), [])
        self.assertEqual(resumen_semana(self.usuario, self.hoy)["programadas"], 1)

    def test_siguiente_no_recomienda_si_ya_hay_visita_programada(self):
        Visita.objects.create(
            residencia=self.residencia,
            fecha=self.otro_dia,
            estado=Visita.Estado.PENDIENTE,
        )
        self.assertIsNone(siguiente_residencia(self.usuario, self.hoy))

    def test_orden_no_depende_del_dia_orientativo(self):
        otra = Residencia.objects.create(
            nombre="Santa Marta",
            frecuencia_semanal=1,
            dia_preferido="LUN",
            propietario=self.usuario,
        )
        filas = pendientes_de_la_semana(self.usuario, self.hoy)
        self.assertEqual({f["residencia"] for f in filas}, {self.residencia, otra})


class VistasTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("vistas_tester")
        self.client.force_login(self.usuario)
        zona = Zona.objects.create(nombre="Centro", propietario=self.usuario)
        self.residencia = Residencia.objects.create(
            nombre="San José",
            zona=zona,
            frecuencia_semanal=1,
            propietario=self.usuario,
        )
        self.producto = Producto.objects.create(nombre="Pañales", propietario=self.usuario)
        MovimientoCupon.objects.create(producto=self.producto, cantidad=20)
        Visita.objects.create(
            residencia=self.residencia,
            fecha=timezone.localdate(),
            turno=Visita.Turno.MANANA,
        )

    def test_paginas_principales(self):
        for nombre in [
            "dashboard",
            "agenda",
            "residencia_list",
            "cupones",
            "producto_list",
            "zona_list",
        ]:
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 200, nombre)

    def test_crear_visita_y_marcar_entregada(self):
        otra = Residencia.objects.create(nombre="Santa Marta", propietario=self.usuario)
        respuesta = self.client.post(
            reverse("visita_nueva"),
            {
                "residencia": otra.pk,
                "fecha": timezone.localdate().isoformat(),
                "turno": Visita.Turno.MANANA,
                "estado": Visita.Estado.PENDIENTE,
                "notas": "",
                "lineas-TOTAL_FORMS": "1",
                "lineas-INITIAL_FORMS": "0",
                "lineas-MIN_NUM_FORMS": "0",
                "lineas-MAX_NUM_FORMS": "1000",
                "lineas-0-producto": self.producto.pk,
                "lineas-0-cantidad": "3",
                "lineas-0-cupones": "",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        visita = Visita.objects.get(residencia=otra)
        self.assertEqual(visita.lineas.count(), 1)
        self.assertEqual(visita.total_cupones, 3)

        self.client.post(reverse("visita_estado", args=[visita.pk, "E"]))
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ENTREGADA)


class ZonaCrudTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario("zonas_tester")
        self.client.force_login(self.usuario)

    def test_crear_zona(self):
        respuesta = self.client.post(
            reverse("zona_nueva"),
            {"nombre": "Cornellà de Llobregat", "orden": 1},
        )
        self.assertRedirects(respuesta, reverse("zona_list"))
        self.assertTrue(
            Zona.objects.filter(nombre="Cornellà de Llobregat", orden=1).exists()
        )

    def test_editar_zona(self):
        zona = Zona.objects.create(nombre="Centro", orden=2, propietario=self.usuario)
        respuesta = self.client.post(
            reverse("zona_editar", args=[zona.pk]),
            {"nombre": "Centro Norte", "orden": 5},
        )
        self.assertRedirects(respuesta, reverse("zona_list"))
        zona.refresh_from_db()
        self.assertEqual(zona.nombre, "Centro Norte")
        self.assertEqual(zona.orden, 5)

    def test_no_borrar_zona_con_residencias(self):
        zona = Zona.objects.create(nombre="Centro", propietario=self.usuario)
        Residencia.objects.create(nombre="San José", zona=zona, propietario=self.usuario)
        respuesta = self.client.post(reverse("zona_borrar", args=[zona.pk]))
        self.assertRedirects(respuesta, reverse("zona_list"))
        self.assertTrue(Zona.objects.filter(pk=zona.pk).exists())

    def test_borrar_zona_vacia(self):
        zona = Zona.objects.create(nombre="Centro", propietario=self.usuario)
        respuesta = self.client.post(reverse("zona_borrar", args=[zona.pk]))
        self.assertRedirects(respuesta, reverse("zona_list"))
        self.assertFalse(Zona.objects.filter(pk=zona.pk).exists())


class AutenticacionTests(TestCase):
    def test_paginas_principales_redirigen_a_login(self):
        for nombre in ["dashboard", "agenda", "residencia_list", "cupones", "zona_list"]:
            respuesta = self.client.get(reverse(nombre))
            self.assertEqual(respuesta.status_code, 302, nombre)
            self.assertIn(reverse("login"), respuesta.url)


class PlanTests(TestCase):
    def test_plan_gratis_limita_residencias(self):
        usuario = crear_usuario("plan_tester")
        for indice in range(3):
            Residencia.objects.create(nombre=f"Residencia {indice}", propietario=usuario)
        estado = estado_plan(usuario)
        self.assertFalse(estado["puede_agregar"])
        self.assertEqual(estado["limite_residencias"], 3)


class AislamientoTests(TestCase):
    def test_cada_usuario_solo_ve_sus_residencias(self):
        usuario_a = crear_usuario("propietario_a")
        usuario_b = crear_usuario("propietario_b")
        Residencia.objects.create(nombre="Zona A", propietario=usuario_a)
        Residencia.objects.create(nombre="Zona B", propietario=usuario_b)

        self.client.force_login(usuario_a)
        respuesta = self.client.get(reverse("residencia_list"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Zona A")
        self.assertNotContains(respuesta, "Zona B")

        self.client.force_login(usuario_b)
        respuesta = self.client.get(reverse("residencia_list"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Zona B")
        self.assertNotContains(respuesta, "Zona A")


class ReporteMensualTests(TestCase):
    def test_pdf_se_genera(self):
        usuario = crear_usuario("reporte_tester")
        self.client.force_login(usuario)
        mes = timezone.localdate().strftime("%Y-%m")
        respuesta = self.client.get(reverse("reporte_mensual_pdf"), {"mes": mes})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
