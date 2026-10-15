from tasks import fatorial, somar

def test_somar():
    resultado = somar.apply(args=[5,3]).get()
    assert resultado == 8

def test_fatorial():
    resultado = fatorial.apply(args=[5]).get()
    assert resultado == 120