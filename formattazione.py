def formatta_euro(valore: float) -> str:
    return f"{valore:,.0f} €".replace(",", ".")


def formatta_percentuale(valore: float) -> str:
    return f"{valore * 100:.2f}%".replace(".", ",")
