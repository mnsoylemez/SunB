import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import numpy as np
import pvlib
from pvlib import location
import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math

def calculate_solar_vectors(loc_data, start_year):
    """Verilen konum ve yıl için güneş konumu vektörlerini hesaplar."""
    try:
        start_date = pd.Timestamp(f'{start_year}-01-01 00:00:00', tz='UTC')
        end_date = pd.Timestamp(f'{start_year + 1}-01-01 00:00:00', tz='UTC')
        times_utc = pd.date_range(start_date, end_date, freq='10min', inclusive='left')
        
        loc = location.Location(
            latitude=loc_data['latitude'],
            longitude=loc_data['longitude'],
            tz=loc_data['timezone'],
            altitude=0,
            name=loc_data['name']
        )
        
        times_local = times_utc.tz_convert(loc_data['timezone'])
        solpos = loc.get_solarposition(times_local)
        clearsky = loc.get_clearsky(times_local, model='ineichen', solar_position=solpos)
        
        solpos['daylight'] = clearsky['dni'] > 0
        daylight_solpos = solpos[solpos['daylight']]
        
        zenith_rad = np.radians(daylight_solpos['apparent_zenith'])
        azimuth_rad = np.radians(daylight_solpos['azimuth'])
        
        x = np.sin(zenith_rad) * np.sin(azimuth_rad)
        y = np.sin(zenith_rad) * np.cos(azimuth_rad)
        z = np.cos(zenith_rad)
        
        vectors_df = pd.DataFrame({
            'x': x,
            'y': y,
            'z': z,
            'zenith': daylight_solpos['apparent_zenith'],
            'azimuth': daylight_solpos['azimuth'],
            'dni': clearsky.loc[daylight_solpos.index, 'dni']
        }, index=daylight_solpos.index)
        
        return vectors_df
        
    except Exception as e:
        print(f"Güneş vektörleri hesaplanırken hata oluştu: {e}")
        raise e

def calculate_panel_tilt_angles(vectors_df):
    """Güneş vektör bileşenlerinden panel eğim açılarını hesaplar."""
    ew_tilt = np.degrees(np.arctan2(vectors_df['x'], vectors_df['z']))
    ns_tilt = np.degrees(np.arctan2(vectors_df['y'], vectors_df['z']))
    panel_tilt = vectors_df['zenith']
    
    panel_angles_df = pd.DataFrame({
        'dogu_bati_egimi': ew_tilt,  # Doğu-Batı eğimi
        'kuzey_guney_egimi': ns_tilt,  # Kuzey-Güney eğimi
        'panel_egimi': panel_tilt,  # Panel eğimi (yataydan)
        'panel_azimut': vectors_df['azimuth'],
        'dni': vectors_df['dni']
    }, index=vectors_df.index)
    
    return panel_angles_df

def calculate_energy_production(panel_angles_df, panel_efficiency_decimal, panel_area=1.0):
    """Panel açıları ve DNI'ya göre enerji üretimini hesaplar."""
    time_interval = 1/6  # 10 dakikalık aralıklar için saat cinsinden
    energy_wh = panel_angles_df['dni'] * panel_efficiency_decimal * panel_area * time_interval
    panel_angles_df['enerji_wh'] = energy_wh
    return panel_angles_df

def analyze_angle_requirements(panel_data):
    """Panel sistemi tasarımı için gerekli maksimum eğim açılarını analiz eder."""
    maks_dogu_egimi = panel_data['dogu_bati_egimi'].max()
    maks_bati_egimi = abs(panel_data['dogu_bati_egimi'].min())
    maks_kuzey_egimi = panel_data['kuzey_guney_egimi'].max()
    maks_guney_egimi = abs(panel_data['kuzey_guney_egimi'].min())
    maks_toplam_egim = panel_data['panel_egimi'].max()
    
    # Günlük istatistikler, açık yön isimleriyle
    daily_data = panel_data.resample('D').agg({
        'dogu_bati_egimi': ['min', 'max'],
        'kuzey_guney_egimi': ['min', 'max'],
        'panel_egimi': ['min', 'max'],
        'enerji_wh': 'sum'
    })
    
    daily_data.columns = [
        'maks_bati_egimi' if col[0] == 'dogu_bati_egimi' and col[1] == 'min' else
        'maks_dogu_egimi' if col[0] == 'dogu_bati_egimi' and col[1] == 'max' else
        'maks_guney_egimi' if col[0] == 'kuzey_guney_egimi' and col[1] == 'min' else
        'maks_kuzey_egimi' if col[0] == 'kuzey_guney_egimi' and col[1] == 'max' else
        f"{col[0]}_{col[1]}" for col in daily_data.columns
    ]
    
    daily_data['maks_bati_egimi'] = -daily_data['maks_bati_egimi']  # Negatif değerleri pozitife çevir
    daily_data['maks_guney_egimi'] = -daily_data['maks_guney_egimi']  # Negatif değerleri pozitife çevir
    
    daily_data.index = daily_data.index.strftime('%Y-%m-%d')
    
    # Aylık istatistikler
    monthly_data = panel_data.resample('ME').agg({
        'dogu_bati_egimi': ['min', 'max'],
        'kuzey_guney_egimi': ['min', 'max'],
        'panel_egimi': ['min', 'max'],
        'enerji_wh': 'sum'
    })
    
    monthly_data.columns = [
        'maks_bati_egimi' if col[0] == 'dogu_bati_egimi' and col[1] == 'min' else
        'maks_dogu_egimi' if col[0] == 'dogu_bati_egimi' and col[1] == 'max' else
        'maks_guney_egimi' if col[0] == 'kuzey_guney_egimi' and col[1] == 'min' else
        'maks_kuzey_egimi' if col[0] == 'kuzey_guney_egimi' and col[1] == 'max' else
        f"{col[0]}_{col[1]}" for col in monthly_data.columns
    ]
    
    monthly_data['maks_bati_egimi'] = -monthly_data['maks_bati_egimi']  # Negatif değerleri pozitife çevir
    monthly_data['maks_guney_egimi'] = -monthly_data['maks_guney_egimi']  # Negatif değerleri pozitife çevir
    
    monthly_data.index = monthly_data.index.strftime('%Y-%m')
    
    # Enerjiyi kWh'ye çevir
    daily_data['enerji_kwh_toplami'] = daily_data['enerji_wh_sum'] / 1000
    daily_data.drop(columns=['enerji_wh_sum'], inplace=True)
    
    monthly_data['enerji_kwh_toplami'] = monthly_data['enerji_wh_sum'] / 1000
    monthly_data.drop(columns=['enerji_wh_sum'], inplace=True)
    
    return {
        'maks_dogu_egimi': maks_dogu_egimi,
        'maks_bati_egimi': maks_bati_egimi,
        'maks_kuzey_egimi': maks_kuzey_egimi,
        'maks_guney_egimi': maks_guney_egimi,
        'maks_toplam_egim': maks_toplam_egim,
        'gunluk_veriler': daily_data,
        'aylik_veriler': monthly_data
    }

def generate_plots(panel_data, analysis_results, loc_name):
    """Güneş açıları ve enerji görselleştirmesi için grafikler oluşturur."""
    fig = plt.figure(figsize=(10, 12))
    
    # Grafik 1: Doğu-Batı eğim açısı
    ax1 = fig.add_subplot(3, 1, 1)
    ax1.plot(panel_data.index, panel_data['dogu_bati_egimi'], 'b-', alpha=0.5)
    ax1.set_ylabel('Doğu-Batı Eğimi (derece)')
    ax1.set_title(f'{loc_name} için Doğu-Batı Eğim Açısı\n(Pozitif = Doğu, Negatif = Batı)')
    ax1.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax1.text(0.02, 0.98, 'Pozitif: Doğuya Eğim\nNegatif: Batıya Eğim', 
             transform=ax1.transAxes, verticalalignment='top', 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Grafik 2: Kuzey-Güney eğim açısı
    ax2 = fig.add_subplot(3, 1, 2)
    ax2.plot(panel_data.index, panel_data['kuzey_guney_egimi'], 'g-', alpha=0.5)
    ax2.set_ylabel('Kuzey-Güney Eğimi (derece)')
    ax2.set_title('Kuzey-Güney Eğim Açısı\n(Pozitif = Kuzey, Negatif = Güney)')
    ax2.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    ax2.text(0.02, 0.98, 'Pozitif: Kuzeye Eğim\nNegatif: Güneye Eğim', 
             transform=ax2.transAxes, verticalalignment='top', 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Grafik 3: Günlük enerji üretimi
    ax3 = fig.add_subplot(3, 1, 3)
    daily_energy = panel_data['enerji_wh'].resample('D').sum() / 1000
    ax3.plot(daily_energy.index, daily_energy, 'r-')
    ax3.set_ylabel('Enerji (kWh/gün)')
    ax3.set_title('Günlük Enerji Üretimi')
    
    fig.tight_layout()
    return fig

def calculate_and_export_vectors(locations_data, start_year, panel_efficiency_decimal, filepath=None):
    """Güneş vektör verilerini hesaplar ve dışa aktarır."""
    if not filepath:
        messagebox.showerror("Hata", "Kayıt dosya yolu belirtilmedi.")
        return
    
    if not (0 < panel_efficiency_decimal <= 1.0):
        messagebox.showerror("Girdi Hatası", "Panel verimliliği %0 ile %100 arasında olmalıdır.")
        return
    
    try:
        tum_analizler = {}
        tum_gunluk_veriler = {}
        tum_aylik_veriler = {}
        tum_grafikler = {}
        
        for loc_data in locations_data:
            print(f"{loc_data['name']} işleniyor...")
            
            vectors_df = calculate_solar_vectors(loc_data, start_year)
            panel_angles_df = calculate_panel_tilt_angles(vectors_df)
            energy_df = calculate_energy_production(panel_angles_df, panel_efficiency_decimal)
            analysis_results = analyze_angle_requirements(energy_df)
            
            tum_analizler[loc_data['name']] = analysis_results
            tum_gunluk_veriler[loc_data['name']] = analysis_results['gunluk_veriler']
            tum_aylik_veriler[loc_data['name']] = analysis_results['aylik_veriler']
            
            fig = generate_plots(energy_df, analysis_results, loc_data['name'])
            tum_grafikler[loc_data['name']] = fig
            
            fig_filepath = f"{os.path.splitext(filepath)[0]}_{loc_data['name']}_grafikler.png"
            fig.savefig(fig_filepath)
            plt.close(fig)
        
        ozet_veriler = []
        for name, analysis in tum_analizler.items():
            ozet_veriler.append({
                'Konum': name,
                'Max Doğu Eğimi (derece)': analysis['maks_dogu_egimi'],
                'Max Batı Eğimi (derece)': analysis['maks_bati_egimi'],
                'Max Kuzey Eğimi (derece)': analysis['maks_kuzey_egimi'],
                'Max Güney Eğimi (derece)': analysis['maks_guney_egimi'],
                'Max Toplam Eğim (derece)': analysis['maks_toplam_egim']
            })
        
        ozet_df = pd.DataFrame(ozet_veriler)
        
        birlesik_gunluk_veriler = {}
        for name, daily_df in tum_gunluk_veriler.items():
            for col in daily_df.columns:
                birlesik_gunluk_veriler[f"{name}_{col}"] = daily_df[col]
        
        birlesik_gunluk_df = pd.DataFrame(birlesik_gunluk_veriler)
        
        birlesik_aylik_veriler = {}
        for name, monthly_df in tum_aylik_veriler.items():
            for col in monthly_df.columns:
                birlesik_aylik_veriler[f"{name}_{col}"] = monthly_df[col]
        
        birlesik_aylik_df = pd.DataFrame(birlesik_aylik_veriler)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            ozet_df.to_excel(writer, sheet_name='Özet', index=False)
            birlesik_gunluk_df.to_excel(writer, sheet_name='Günlük Veriler')
            birlesik_aylik_df.to_excel(writer, sheet_name='Aylık Veriler')
            
            bilgi_verileri = pd.DataFrame({
                'Sütun': [
                    'dogu_bati_egimi', 'kuzey_guney_egimi', 'panel_egimi', 'maks_bati_egimi',
                    'maks_dogu_egimi', 'maks_guney_egimi', 'maks_kuzey_egimi', 'enerji_kwh_toplami'
                ],
                'Açıklama': [
                    'Doğu-Batı yönündeki eğim (pozitif = Doğu, negatif = Batı)',
                    'Kuzey-Güney yönündeki eğim (pozitif = Kuzey, negatif = Güney)',
                    'Yataydan eğim (0° = düz, 90° = dikey)',
                    'Günlük/aylık batıya maksimum eğim (pozitif derece)',
                    'Günlük/aylık doğuya maksimum eğim (pozitif derece)',
                    'Günlük/aylık güneye maksimum eğim (pozitif derece)',
                    'Günlük/aylık kuzeye maksimum eğim (pozitif derece)',
                    'Günlük/aylık toplam enerji üretimi (kWh)'
                ]
            })
            bilgi_verileri.to_excel(writer, sheet_name='Bilgi', index=False)
        
        messagebox.showinfo("Başarılı", 
                           f"Güneş paneli eğim açıları ve enerji üretim verileri şuraya kaydedildi:\n"
                           f"{filepath}\n\n"
                           f"Görsel grafikler şuraya kaydedildi:\n"
                           f"{os.path.splitext(filepath)[0]}_[KONUM]_grafikler.png\n\n"
                           f"Not: Bu, açık gökyüzünde koşullarında 1m² izleyici panel için potansiyel "
                           f"değerleri temsil eder.")
        
        if tum_grafikler:
            return list(tum_grafikler.values())[0]
        
    except Exception as e:
        messagebox.showerror("Hata", f"Beklenmedik bir hata oluştu:\n{e}")
        import traceback
        traceback.print_exc()
        return None

class SolarTiltApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Güneş Paneli Maksimum Eğim Açıları Hesaplayıcı")
        self.root.geometry("800x700")
        
        self.input_frame = ttk.LabelFrame(root, text="Girdiler", padding=(10, 5))
        self.input_frame.pack(padx=10, pady=10, fill="x")
        
        self.plot_frame = ttk.LabelFrame(root, text="Grafik", padding=(10, 5))
        self.plot_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.tz_display_options = []
        self.tz_value_map = {}
        for offset in range(-12, 15):
            display = f"GMT{offset:+d}"
            value = f"Etc/GMT{-offset:+d}"
            self.tz_display_options.append(display)
            self.tz_value_map[display] = value
        
        self.default_tz_display = "GMT+3"
        
        self.locations_entries = []
        self.add_location_fields(1)
        
        add_loc_button = ttk.Button(self.input_frame, text="+ Konum Ekle", command=self.add_location)
        add_loc_button.pack(pady=5)
        
        config_frame = ttk.Frame(self.input_frame)
        config_frame.pack(fill="x", pady=5, padx=5)
        
        ttk.Label(config_frame, text="Başlangıç Yılı:").pack(side=tk.LEFT, padx=5)
        self.year_entry = ttk.Entry(config_frame, width=8)
        self.year_entry.pack(side=tk.LEFT)
        current_year = datetime.datetime.now().year
        self.year_entry.insert(0, str(current_year - 1))
        
        ttk.Label(config_frame, text="Panel Verimliliği (%):").pack(side=tk.LEFT, padx=(20, 5))
        self.efficiency_entry = ttk.Entry(config_frame, width=6)
        self.efficiency_entry.pack(side=tk.LEFT)
        self.efficiency_entry.insert(0, "20")
        
        ttk.Label(config_frame, text="(1 yıl için)").pack(side=tk.LEFT, padx=10)
        
        calculate_button = ttk.Button(
            root, 
            text="Hesapla ve Eğim Açılarını Dışa Aktar", 
            command=self.on_calculate_click
        )
        calculate_button.pack(padx=10, pady=10)
        
        help_text = ("Bu program, verilen konumda 1m² panel için maksimum gerekli eğim açılarını hesaplar.\n"
                    "Doğu-Batı ve Kuzey-Güney yönlerindeki maksimum eğim açıları, panel tasarımı için kullanılabilir.\n"
                    "Hesaplama, güneş ışınlarının panele dik gelmesi için gerekli açıları belirler.")
        help_label = ttk.Label(root, text=help_text, wraplength=780, justify=tk.CENTER)
        help_label.pack(padx=10, pady=5)
        
        self.canvas = None
    
    def add_location_fields(self, loc_num):
        """Yeni bir konum için giriş alanları ekler."""
        loc_frame = ttk.Frame(self.input_frame)
        loc_frame.pack(fill="x", pady=5)
        ttk.Label(loc_frame, text=f"Konum {loc_num}:").grid(row=0, column=0, columnspan=4, sticky="w", padx=5)
        
        ttk.Label(loc_frame, text="İsim:").grid(row=1, column=0, sticky="w", padx=5)
        name_entry = ttk.Entry(loc_frame, width=15)
        name_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5)
        
        ttk.Label(loc_frame, text="Enlem (°):").grid(row=2, column=0, sticky="w", padx=5)
        lat_entry = ttk.Entry(loc_frame, width=10)
        lat_entry.grid(row=2, column=1, sticky="ew", padx=5)
        
        ttk.Label(loc_frame, text="Boylam (°):").grid(row=2, column=2, sticky="w", padx=5)
        lon_entry = ttk.Entry(loc_frame, width=10)
        lon_entry.grid(row=2, column=3, sticky="ew", padx=5)
        
        ttk.Label(loc_frame, text="Saat Dilimi:").grid(row=3, column=0, sticky="w", padx=5)
        tz_combo = ttk.Combobox(loc_frame, values=self.tz_display_options, state="readonly", width=10)
        tz_combo.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5)
        tz_combo.set(self.default_tz_display)
        
        loc_frame.columnconfigure(1, weight=1)
        loc_frame.columnconfigure(3, weight=1)
        
        entry_dict = {'name': name_entry, 'lat': lat_entry, 'lon': lon_entry, 'tz_combo': tz_combo}
        self.locations_entries.append(entry_dict)
        return entry_dict
    
    def add_location(self):
        """Yeni bir konum ekler."""
        loc_num = len(self.locations_entries) + 1
        self.add_location_fields(loc_num)
    
    def display_plot(self, fig):
        """Grafiği GUI'de gösterir."""
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def on_calculate_click(self):
        """Hesaplama işlemini başlatır ve sonuçları dışa aktarır."""
        locations_data = []
        try:
            start_year = int(self.year_entry.get())
            efficiency_percent = float(self.efficiency_entry.get())
            
            if not (0 < efficiency_percent <= 100):
                raise ValueError("Panel Verimliliği %0 ile %100 arasında olmalıdır.")
            panel_efficiency_decimal = efficiency_percent / 100.0
            
            if start_year < 1950 or start_year > 2100:
                raise ValueError("Yıl 1950 ile 2100 arasında olmalıdır")

            for i, entries in enumerate(self.locations_entries):
                name = entries['name'].get().strip()
                lat_str = entries['lat'].get()
                lon_str = entries['lon'].get()
                selected_display_tz = entries['tz_combo'].get()
                
                if not all([name, lat_str, lon_str, selected_display_tz]):
                    messagebox.showerror("Girdi Hatası", f"Lütfen Konum {i+1} için tüm alanları doldurun.")
                    return
                
                try:
                    tz_value = self.tz_value_map[selected_display_tz]
                except KeyError:
                    messagebox.showerror("Girdi Hatası", f"Konum {i+1} için geçersiz saat dilimi seçildi.")
                    return
                
                locations_data.append({
                    'name': name,
                    'latitude': float(lat_str),
                    'longitude': float(lon_str),
                    'timezone': tz_value
                })
            
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel dosyaları", "*.xlsx"), ("Tüm dosyalar", "*.*")],
                title="Açı ve Enerji Verisini Farklı Kaydet..."
            )
            
            if save_path:
                fig = calculate_and_export_vectors(
                    locations_data,
                    start_year,
                    panel_efficiency_decimal,
                    filepath=save_path
                )
                
                if fig:
                    self.display_plot(fig)
            else:
                print("Kaydetme işlemi iptal edildi.")
        
        except ValueError as ve:
            messagebox.showerror("Girdi Hatası", f"Lütfen Yıl, Verimlilik, Enlem ve Boylam için geçerli sayılar girin.\nDetaylar: {ve}")
        except Exception as e:
            messagebox.showerror("Hata", f"Girdi işlenirken beklenmedik bir hata oluştu:\n{e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = tk.Tk()
    app = SolarTiltApp(root)
    root.mainloop()