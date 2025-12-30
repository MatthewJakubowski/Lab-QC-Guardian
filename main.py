import math
import datetime
import matplotlib.pyplot as plt # 📈 Biblioteka do wykresów

# --- MODUŁ 1: Wczytywanie ---
def wczytaj_dane(nazwa_pliku):
    print(f"📂 Otwieram plik: {nazwa_pliku}...")
    wyniki = []
    try:
        with open(nazwa_pliku, 'r') as plik:
            for linia in plik:
                if linia.strip():
                    wyniki.append(float(linia.strip()))
        return wyniki
    except FileNotFoundError:
        print("❌ Błąd: Brak pliku!")
        return []

# --- MODUŁ 2: Statystyka ---
def oblicz_statystyke(dane):
    n = len(dane)
    if n < 2: return None
    srednia = sum(dane) / n
    suma_kwadratow = sum((x - srednia) ** 2 for x in dane)
    sd = math.sqrt(suma_kwadratow / (n - 1))
    return srednia, sd

# --- MODUŁ 3: Raport Tekstowy + Logi ---
def generuj_raport(dane, srednia, sd):
    teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tekst = f"\n📅 RAPORT [{teraz}]\n"
    tekst += f"📊 Średnia={srednia:.2f}, SD={sd:.2f}\n"
    tekst += "-" * 40 + "\n"
    
    bledy = 0
    for i, wynik in enumerate(dane, 1):
        z_score = (wynik - srednia) / sd
        ocena = "OK"
        if abs(z_score) > 2: ocena = "⚠️ OSTRZEŻENIE"
        if abs(z_score) > 3: 
            ocena = "❌ BŁĄD"
            bledy += 1
        tekst += f"{i:<3} | {wynik:<6.1f} | {z_score:<5.2f} | {ocena}\n"
    
    tekst += "-" * 40 + "\n"
    tekst += "WNIOSKI: " + ("ODRZUCONO 🚨" if bledy > 0 else "ZAAKCEPTOWANO ✅") + "\n\n"
    return tekst

def zapisz_log(tresc):
    with open("dziennik_qc.txt", "a") as f:
        f.write(tresc)
    print("💾 Log zapisany.")

# --- MODUŁ 4: Wizualizacja (NOWOŚĆ!) ---
def rysuj_wykres(dane, srednia, sd):
    print("🎨 Generuję Wykres Levey-Jenningsa...")
    
    # Oś X (numer pomiaru) i Oś Y (wartości)
    x = list(range(1, len(dane) + 1))
    y = dane
    
    plt.figure(figsize=(10, 6)) # Rozmiar obrazka
    
    # 1. Rysujemy punkty połączone linią
    plt.plot(x, y, marker='o', linestyle='-', color='blue', label='Wyniki QC')
    
    # 2. Rysujemy linie poziome (Średnia, SD)
    plt.axhline(srednia, color='green', linewidth=2, label='Średnia')
    plt.axhline(srednia + 2*sd, color='orange', linestyle='--', label='+2 SD')
    plt.axhline(srednia - 2*sd, color='orange', linestyle='--', label='-2 SD')
    plt.axhline(srednia + 3*sd, color='red', linestyle=':', label='+3 SD')
    plt.axhline(srednia - 3*sd, color='red', linestyle=':', label='-3 SD')
    
    # 3. Opisy
    plt.title("Karta Kontrolna Levey-Jenningsa")
    plt.xlabel("Numer Pomiaru")
    plt.ylabel("Stężenie (mg/dL)")
    plt.legend() # Pokaż legendę
    plt.grid(True, alpha=0.3) # Siatka w tle
    
    # 4. Zapisz do pliku
    nazwa_pliku = "wykres_qc.png"
    plt.savefig(nazwa_pliku)
    print(f"🖼️ Wykres zapisany jako: {nazwa_pliku}")
    
    # (Opcjonalnie) Pokaż na ekranie - w Pydroid to otworzy nowe okno
    # plt.show() 

# --- MAIN ---
print("--- 🛡️ LAB QC GUARDIAN v1.0 ---")
lista = wczytaj_dane("dane_qc.txt")

if lista:
    stat = oblicz_statystyke(lista)
    if stat:
        sr, sd = stat
        raport = generuj_raport(lista, sr, sd)
        print(raport)
        zapisz_log(raport)
        
        # Odpalamy rysowanie!
        rysuj_wykres(lista, sr, sd)
