from django import forms
from django.forms import inlineformset_factory

from .models import (
    MovimientoCupon,
    Producto,
    Residencia,
    Visita,
    VisitaProducto,
)

TEXTO = {"class": "campo"}
AREA = {"class": "campo", "rows": 2}


class ResidenciaForm(forms.ModelForm):
    class Meta:
        model = Residencia
        fields = [
            "nombre",
            "direccion",
            "zona",
            "contacto",
            "telefono",
            "horario",
            "orden_ruta",
            "frecuencia_semanal",
            "dia_preferido",
            "notas",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={**TEXTO, "placeholder": "Residencia San José"}),
            "direccion": forms.TextInput(attrs={**TEXTO, "placeholder": "Calle, número, piso"}),
            "zona": forms.Select(attrs=TEXTO),
            "contacto": forms.TextInput(attrs={**TEXTO, "placeholder": "Nombre de la persona"}),
            "telefono": forms.TextInput(attrs={**TEXTO, "placeholder": "600 000 000", "inputmode": "tel"}),
            "horario": forms.TextInput(attrs={**TEXTO, "placeholder": "09:00 - 13:00"}),
            "orden_ruta": forms.NumberInput(attrs={**TEXTO, "min": 0}),
            "frecuencia_semanal": forms.NumberInput(attrs={**TEXTO, "min": 1, "max": 7}),
            "dia_preferido": forms.Select(attrs=TEXTO),
            "notas": forms.Textarea(attrs={**AREA, "placeholder": "Portero, llaves, accesos..."}),
            "activo": forms.CheckboxInput(attrs={"class": "interruptor"}),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre",
            "descripcion",
            "cupones_por_unidad",
            "stock_minimo",
            "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={**TEXTO, "placeholder": "Pañal talla M"}),
            "descripcion": forms.TextInput(attrs={**TEXTO, "placeholder": "Detalle opcional"}),
            "cupones_por_unidad": forms.NumberInput(attrs={**TEXTO, "min": 1}),
            "stock_minimo": forms.NumberInput(attrs={**TEXTO, "min": 0}),
            "activo": forms.CheckboxInput(attrs={"class": "interruptor"}),
        }


class MovimientoCuponForm(forms.ModelForm):
    class Meta:
        model = MovimientoCupon
        fields = ["producto", "fecha", "cantidad", "tipo", "notas"]
        widgets = {
            "producto": forms.Select(attrs=TEXTO),
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={**TEXTO, "type": "date"}),
            "cantidad": forms.NumberInput(attrs={**TEXTO, "placeholder": "Ej. 50"}),
            "tipo": forms.Select(attrs=TEXTO),
            "notas": forms.TextInput(attrs={**TEXTO, "placeholder": "Ej. compra semanal"}),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad") or 0
        if cantidad == 0:
            raise forms.ValidationError("Indica una cantidad distinta de cero.")
        return cantidad


class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = ["residencia", "fecha", "turno", "estado", "notas"]
        widgets = {
            "residencia": forms.Select(attrs=TEXTO),
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={**TEXTO, "type": "date"}),
            "turno": forms.Select(attrs=TEXTO),
            "estado": forms.Select(attrs=TEXTO),
            "notas": forms.Textarea(attrs={**AREA, "placeholder": "Observaciones de la visita"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["residencia"].queryset = Residencia.objects.filter(
            activo=True
        ).select_related("zona")
        if not self.instance.pk:
            self.fields["residencia"].empty_label = "Elige residencia..."
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]


class VisitaProductoForm(forms.ModelForm):
    class Meta:
        model = VisitaProducto
        fields = ["producto", "cantidad", "cupones"]
        widgets = {
            "producto": forms.Select(attrs={"class": "campo campo-producto"}),
            "cantidad": forms.NumberInput(
                attrs={"class": "campo campo-cantidad", "min": 1}
            ),
            "cupones": forms.NumberInput(
                attrs={
                    "class": "campo campo-cupones",
                    "min": 0,
                    "placeholder": "Auto",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(activo=True)
        self.fields["producto"].empty_label = "Producto..."
        self.fields["cupones"].required = False
        self.fields["cupones"].help_text = "Vacío = unidades x cupones por unidad"


VisitaProductoFormSet = inlineformset_factory(
    Visita,
    VisitaProducto,
    form=VisitaProductoForm,
    extra=1,
    can_delete=True,
    validate_min=False,
)
