from tasks import fatorial, somar

def test_somar():
    resultado = somar.apply(args=[5,3]).get()
    assert resultado == 8

def test_fatorial():
    resultado = fatorial.apply(args=[5]).get()
    assert resultado == 120


# Caso o n seja zero
def test_fatorial_de_zero():
    resultado = fatorial.apply(args=[0]).get()
    assert resultado == 1