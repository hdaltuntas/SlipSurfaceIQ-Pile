"""
Every text of SlipSurface IQ Pile, in English and Turkish.

Each entry is written once as ``key: (English, Turkish)`` so the two languages
cannot drift apart: a key without its translation is a syntax error, not a
blank on the screen. `TRANSLATIONS[lang][key]` is how the rest of the program
reads them.
"""

from __future__ import annotations

ENTRIES = {
    # ------------------------------------------------------------------ input errors
    "err_dimensions": ("The pile diameter and length must be greater than zero.",
                       "Kazık çapı ve boyu sıfırdan büyük olmalıdır."),
    "err_top": ("The depth of the pile head cannot be negative.",
                "Kazık başı derinliği negatif olamaz."),
    "err_material": ("The unit weight and the modulus of the pile must be greater than zero.",
                     "Kazık malzemesinin birim hacim ağırlığı ve modülü sıfırdan büyük "
                     "olmalıdır."),
    "err_load": ("The load on the group must be greater than zero.",
                 "Gruba gelen yük sıfırdan büyük olmalıdır."),
    "err_group_count": ("A group has at least one pile in each direction.",
                        "Grupta her iki yönde de en az bir kazık bulunmalıdır."),
    "err_group_spacing": ("The pile spacing cannot be smaller than the pile diameter.",
                          "Kazık aralığı kazık çapından küçük olamaz."),
    "err_gamma": ("Layer '{name}': γ must be positive and γsat greater than γw.",
                  "'{name}' tabakası: γ pozitif, γdoy ise γw'den büyük olmalıdır."),
    "err_phi": ("Layer '{name}': the friction angle must be between 0 and 50°.",
                "'{name}' tabakası: içsel sürtünme açısı 0 ile 50° arasında olmalıdır."),
    "err_nu": ("Layer '{name}': Poisson's ratio must be between 0 and 0.5.",
               "'{name}' tabakası: Poisson oranı 0 ile 0.5 arasında olmalıdır."),
    "err_cu": ("Layer '{name}' is cohesive and needs an undrained strength cu.",
               "'{name}' tabakası kohezyonlu; drenajsız kayma dayanımı cu gereklidir."),
    "err_granular_phi": ("Layer '{name}' is granular and needs a friction angle φ'.",
                         "'{name}' tabakası granüler; içsel sürtünme açısı φ' gereklidir."),
    "err_E": ("Layer '{name}' needs a modulus E greater than zero.",
              "'{name}' tabakası için sıfırdan büyük bir E modülü gereklidir."),
    "err_no_layers": ("The soil profile has no layer with a thickness.",
                      "Zemin profilinde kalınlığı girilmiş tabaka yok."),
    "err_tip_below": ("The pile tip ({tip:.2f} m) must lie within the soil profile "
                      "({depth:.2f} m).",
                      "Kazık ucu ({tip:.2f} m) zemin profilinin ({depth:.2f} m) içinde "
                      "olmalıdır."),
    "err_socket_D": ("The socket diameter must be greater than zero.",
                     "Soket çapı sıfırdan büyük olmalıdır."),
    "err_socket_Ls": ("The socket length cannot be negative.",
                      "Soket boyu negatif olamaz."),
    "err_socket_rock_depth": ("The rock surface must lie at or below the pile head.",
                              "Kaya yüzeyi kazık başının altında ya da hizasında olmalıdır."),
    "err_socket_load": ("The load on the socketed pile must be greater than zero.",
                        "Soketli kazığa gelen yük sıfırdan büyük olmalıdır."),
    "err_socket_qu": ("The rock strength qu and the concrete strength f'c must be greater "
                      "than zero.",
                      "Kaya dayanımı qu ve beton dayanımı f'c sıfırdan büyük olmalıdır."),
    "err_socket_modulus": ("The rock and concrete moduli must be greater than zero.",
                           "Kaya ve beton modülleri sıfırdan büyük olmalıdır."),
    "err_socket_nu": ("Poisson's ratio of the rock must be between 0 and 0.5.",
                      "Kayanın Poisson oranı 0 ile 0.5 arasında olmalıdır."),

    # ------------------------------------------------------------------ warnings
    "warn_weak_below": ("'{name}', a weaker layer, lies within {n:.0f} diameters below the "
                        "tip: the base resistance may be lower than computed.",
                        "Uçun {n:.0f} çap altında daha zayıf '{name}' tabakası var: uç "
                        "direnci hesaplanandan düşük olabilir."),
    "warn_meyerhof_limit": ("Meyerhof's limit governs the base: qb = 0.5·pa·Nq*·tan φ' = "
                            "{limit:,.0f} kPa.",
                            "Uçta Meyerhof sınırı belirleyici: qb = 0.5·pa·Nq*·tan φ' = "
                            "{limit:,.0f} kPa."),
    "warn_spacing": ("The spacing {s:.2f} m is less than {n:.1f}·D (D = {D:.2f} m); the "
                     "usual minimum is 2.5 to 3 diameters.",
                     "{s:.2f} m aralık {n:.1f}·D değerinden küçük (D = {D:.2f} m); olağan "
                     "en küçük aralık 2.5–3 çaptır."),
    "warn_beta_phi": ("The β method needs φ' in the clay layers; a clay with φ' = 0 gives no "
                      "shaft friction by it.",
                      "β yöntemi kil tabakalarında φ' ister; φ' = 0 olan kil bu yöntemle "
                      "çevre sürtünmesi vermez."),
    "warn_spt_bored": ("Meyerhof's SPT rule was derived for driven piles; for a bored pile it "
                       "is shown for comparison only.",
                       "Meyerhof SPT kuralı çakma kazıklar için türetilmiştir; fore kazıkta "
                       "yalnızca karşılaştırma için gösterilir."),
    "warn_critical_depth": ("Below the critical depth zc = {zc:.2f} m the shaft friction and "
                            "the base resistance in sand no longer grow with depth.",
                            "Kritik derinlik zc = {zc:.2f} m altında kumdaki çevre sürtünmesi "
                            "ve uç direnci derinlikle artmaz."),
    "warn_raft_bottom": ("The stresses under the equivalent raft still matter at the foot of "
                         "the profile ({depth:.2f} m); layers below it would settle too.",
                         "Eşdeğer radye altındaki gerilmeler profilin tabanında ({depth:.2f} m) "
                         "hâlâ önemli; daha derindeki tabakalar da oturur."),
    "warn_meyerhof_settlement": ("Meyerhof's SPT settlement needs a granular layer with N60 "
                                 "at the tip; the equivalent raft was used for the check.",
                                 "Meyerhof SPT oturması uçta N60 değeri olan granüler tabaka "
                                 "ister; kontrolde eşdeğer radye kullanıldı."),
    "warn_no_length": ("No length down to the foot of the profile ({hi:.2f} m below the head) "
                       "satisfies both checks.",
                       "Profil tabanına kadar (kazık başından {hi:.2f} m) hiçbir boy iki "
                       "kontrolü birden sağlamıyor."),
    "warn_socket_concrete": ("The concrete (f'c = {fc:.1f} MPa) is weaker than the rock "
                             "(qu = {qu:.1f} MPa): the side shear uses f'c.",
                             "Beton (f'c = {fc:.1f} MPa) kayadan (qu = {qu:.1f} MPa) zayıf: "
                             "yanal sürtünmede f'c kullanıldı."),
    "warn_socket_weak": ("qu = {qu:.1f} MPa is above {limit:.1f} MPa: the linear rules fitted "
                         "to weak rock are left out of the statistics.",
                         "qu = {qu:.1f} MPa, {limit:.1f} MPa'nın üstünde: zayıf kayaya "
                         "uydurulmuş doğrusal kurallar istatistiklere katılmadı."),
    "warn_socket_design_weak": ("The correlation chosen for the design is outside its range "
                                "for this rock.",
                                "Tasarım için seçilen bağıntı bu kaya için geçerlilik "
                                "aralığının dışında."),
    "warn_socket_ksp": ("The joints are outside the range of the CFEM Ksp method "
                        "(0.05 < c/D < 2, δ/c < 0.02).",
                        "Süreksizlikler CFEM Ksp yönteminin aralığı dışında "
                        "(0.05 < c/D < 2, δ/c < 0.02)."),
    "warn_socket_no_length": ("No socket up to {hi:.0f} m carries the load with the design "
                              "side shear.",
                              "Tasarım yanal sürtünmesiyle {hi:.0f} m'ye kadar hiçbir soket "
                              "yükü taşımıyor."),
    "warn_socket_short": ("The socket being checked (Ls = {Ls:.2f} m) is shorter than the "
                          "design length {need:.2f} m.",
                          "Kontrol edilen soket (Ls = {Ls:.2f} m) tasarım boyu {need:.2f} m'den "
                          "kısa."),
    "warn_socket_base_concrete": ("The design base resistance {qb:.1f} MPa exceeds the "
                                  "concrete strength f'c = {fc:.1f} MPa; check the pile "
                                  "structurally.",
                                  "Tasarım uç direnci {qb:.1f} MPa, beton dayanımı "
                                  "f'c = {fc:.1f} MPa'yı aşıyor; kazığı yapısal olarak kontrol "
                                  "ediniz."),

    # ------------------------------------------------------------------ input groups
    "group_project": ("Project", "Proje"),
    "title_label": ("Title", "Başlık"),
    "analyst_label": ("Analyst", "Hazırlayan"),
    "group_pile": ("Pile", "Kazık"),
    "shape_label": ("Cross-section", "Kesit"),
    "D_label": ("Diameter / side D", "Çap / kenar D"),
    "L_label": ("Length L", "Boy L"),
    "top_label": ("Depth of the pile head", "Kazık başı derinliği"),
    "installation_label": ("Installation", "İmalat yöntemi"),
    "gamma_p_label": ("Unit weight γp", "Birim hacim ağırlık γp"),
    "Ep_label": ("Modulus Ep", "Elastisite modülü Ep"),
    "pile_note": ("L is measured from the pile head, which sits at the underside of the cap. "
                  "The installation sets the earth pressure along the shaft.",
                  "L kazık başından ölçülür; kazık başı başlık altındadır. İmalat yöntemi "
                  "gövde boyunca yanal toprak basıncını belirler."),
    "group_loading": ("Load", "Yük"),
    "Q_label": ("Vertical load on the group Q", "Gruba gelen düşey yük Q"),
    "loading_note": ("The whole load at the underside of the cap, its own weight included; "
                     "each pile carries Q/n.",
                     "Başlık altındaki toplam yük, başlığın kendi ağırlığı dahil; her kazık "
                     "Q/n taşır."),
    "group_group": ("Pile group", "Kazık grubu"),
    "nx_label": ("Piles along B", "B yönünde kazık"),
    "ny_label": ("Piles along L", "L yönünde kazık"),
    "sx_label": ("Spacing along B", "B yönünde aralık"),
    "sy_label": ("Spacing along L", "L yönünde aralık"),
    "efficiency_label": ("Group efficiency", "Grup verimi"),
    "block_label": ("Check block failure", "Blok göçmesini kontrol et"),
    "group_note": ("1 × 1 is a single pile. The group capacity is the smaller of η·n·Qult "
                   "and block failure.",
                   "1 × 1 tek kazıktır. Grubun taşıma gücü η·n·Qult ile blok göçmesinin "
                   "küçüğüdür."),
    "group_water": ("Groundwater", "Yeraltı suyu"),
    "water_depth_label": ("Water table depth", "Su tablası derinliği"),
    "gamma_w_label": ("Unit weight of water γw", "Suyun birim hacim ağırlığı γw"),
    "group_methods": ("Methods", "Yöntemler"),
    "clay_method_label": ("Shaft friction in clay", "Kilde çevre sürtünmesi"),
    "sladen_C_label": ("Sladen's C (0: by installation)", "Sladen C (0: imalata göre)"),
    "tip_method_label": ("Base resistance", "Uç direnci"),
    "janbu_eta_label": ("Janbu's angle η'", "Janbu açısı η'"),
    "K_ratio_label": ("K / K0 in sand (0: by installation)", "Kumda K / K0 (0: imalata göre)"),
    "delta_ratio_label": ("Interface friction δ / φ'", "Arayüz sürtünmesi δ / φ'"),
    "critical_depth_label": ("Critical depth in sand", "Kumda kritik derinlik"),
    "zc_ratio_label": ("Critical depth zc / D", "Kritik derinlik zc / D"),
    "spt_method_label": ("Meyerhof's SPT rule beside them", "Yanında Meyerhof SPT kuralı"),
    "methods_note": ("The table of results sets every shaft method against every base "
                     "method; the ones chosen here make the checks.",
                     "Sonuç tablosu her çevre yöntemini her uç yöntemiyle karşılaştırır; "
                     "kontroller burada seçilenlerle yapılır."),
    "group_weight": ("Pile weight", "Kazık ağırlığı"),
    "subtract_weight_label": ("Subtract the weight from the capacity",
                              "Ağırlığı taşıma gücünden düş"),
    "buoyant_weight_label": ("Buoyant below the water table", "Su altında batık ağırlık"),
    "weight_note": ("Qult,net = Qs + Qb − W, W = γp·Ab·L (γp − γw below the water table).",
                    "Qult,net = Qs + Qb − W, W = γp·Ab·L (su altında γp − γw)."),
    "group_settlement": ("Settlement", "Oturma"),
    "group_method_label": ("Group settlement for the check", "Kontrolde grup oturması"),
    "raft_fraction_label": ("Depth of the equivalent raft / L", "Eşdeğer radye derinliği / L"),
    "spread_label": ("Load spread below the raft (V : H)", "Radye altı yük yayılımı (D : Y)"),
    "distribution_label": ("Shaft friction along the pile", "Gövde boyunca sürtünme dağılımı"),
    "settlement_note": ("The equivalent raft sits at 2/3·L below the pile head and spreads "
                        "2 : 1; clays consolidate with Cc, Cr, e0 and OCR.",
                        "Eşdeğer radye kazık başından 2/3·L derindedir ve 2 : 1 yayılır; "
                        "killer Cc, Cr, e0 ve OCR ile konsolide olur."),
    "group_criteria": ("Criteria", "Ölçütler"),
    "FS_label": ("Factor of safety", "Güvenlik sayısı"),
    "s_allow_label": ("Allowable settlement", "İzin verilen oturma"),
    "L_min_label": ("Shortest length tried", "Denenen en kısa boy"),
    "L_step_label": ("Step of the length search", "Boy aramasının adımı"),
    "criteria_note": ("The required length is the shortest pile that passes the single-pile "
                      "and the group check.",
                      "Gerekli boy, tek kazık ve grup kontrollerini sağlayan en kısa "
                      "kazıktır."),
    "group_socket": ("Socketed pile", "Soketli kazık"),
    "socket_D_label": ("Socket diameter D", "Soket çapı D"),
    "socket_Ls_label": ("Socket length to check Ls (0: design)",
                        "Kontrol edilecek soket boyu Ls (0: tasarım)"),
    "socket_top_label": ("Depth of the pile head", "Kazık başı derinliği"),
    "rock_depth_label": ("Depth of the rock surface", "Kaya yüzeyi derinliği"),
    "socket_Q_label": ("Load on the pile Q", "Kazığa gelen yük Q"),
    "socket_note": ("The socket carries the load; the friction of the overburden is ignored, "
                    "its share of the pile's weight is not.",
                    "Yükü soket taşır; örtü tabakasının sürtünmesi ihmal edilir, kazık "
                    "ağırlığındaki payı edilmez."),
    "group_rock": ("Rock", "Kaya"),
    "qu_label": ("Intact rock strength qu", "Sağlam kaya dayanımı qu"),
    "modulus_method_label": ("Rock mass modulus", "Kaya kütlesi modülü"),
    "Ei_label": ("Intact modulus Ei", "Sağlam kaya modülü Ei"),
    "RQD_label": ("RQD", "RQD"),
    "Em_label": ("Rock mass modulus Em", "Kaya kütlesi modülü Em"),
    "GSI_label": ("GSI", "GSI"),
    "mi_label": ("Hoek–Brown mi", "Hoek–Brown mi"),
    "D_blast_label": ("Disturbance factor D", "Örselenme katsayısı D"),
    "nu_r_label": ("Poisson's ratio ν", "Poisson oranı ν"),
    "Eb_ratio_label": ("Modulus below the base / Em", "Uç altı modül / Em"),
    "spacing_label": ("Joint spacing c", "Süreksizlik aralığı c"),
    "aperture_label": ("Joint aperture δ", "Süreksizlik açıklığı δ"),
    "rock_note": ("GSI and mi give the Hoek–Brown base resistance; the joint spacing and "
                  "aperture the CFEM one.",
                  "GSI ve mi Hoek–Brown uç direncini, süreksizlik aralığı ve açıklığı CFEM uç "
                  "direncini verir."),
    "group_concrete": ("Concrete", "Beton"),
    "fc_label": ("Concrete strength f'c", "Beton dayanımı f'c"),
    "Ec_label": ("Concrete modulus Ec", "Beton modülü Ec"),
    "gamma_c_label": ("Unit weight of the concrete", "Betonun birim hacim ağırlığı"),
    "group_socket_design": ("Socket design", "Soket tasarımı"),
    "design_label": ("Design side shear", "Tasarım yanal sürtünmesi"),
    "base_design_label": ("Design base resistance", "Tasarım uç direnci"),
    "FS_side_label": ("Factor of safety on the side", "Yanal sürtünme güvenlik sayısı"),
    "FS_base_label": ("Factor of safety on the base", "Uç direnci güvenlik sayısı"),
    "min_ratio_label": ("Minimum socket length / D", "En küçük soket boyu / D"),
    "weak_rock_label": ("Weak rock limit for the linear rules",
                        "Doğrusal kurallar için zayıf kaya sınırı"),
    "socket_design_note": ("The socket length is computed with every correlation; the design "
                           "length uses the statistic or the correlation chosen here.",
                           "Soket boyu her bağıntıyla hesaplanır; tasarım boyu burada seçilen "
                           "istatistik ya da bağıntıyla bulunur."),

    # ------------------------------------------------------------------ choices
    "shape_circular": ("Circular", "Dairesel"),
    "shape_square": ("Square", "Kare"),
    "installation_bored": ("Bored / CFA", "Fore / CFA"),
    "installation_driven_low": ("Driven, small displacement", "Çakma, az yer değiştiren"),
    "installation_driven_high": ("Driven, large displacement", "Çakma, çok yer değiştiren"),
    "behaviour_granular": ("Granular", "Granüler"),
    "behaviour_cohesive": ("Cohesive", "Kohezyonlu"),
    "method_alpha_api": ("α — API RP 2A", "α — API RP 2A"),
    "method_alpha_kulhawy": ("α — Kulhawy & Phoon", "α — Kulhawy & Phoon"),
    "method_alpha_sladen": ("α — Sladen", "α — Sladen"),
    "method_beta": ("β — Burland", "β — Burland"),
    "method_lambda": ("λ — Vijayvergiya & Focht", "λ — Vijayvergiya & Focht"),
    "method_meyerhof": ("Meyerhof", "Meyerhof"),
    "method_vesic": ("Vesić", "Vesić"),
    "method_janbu": ("Janbu", "Janbu"),
    "method_spt": ("SPT — Meyerhof", "SPT — Meyerhof"),
    "method_granular": ("K·σ'v·tan δ", "K·σ'v·tan δ"),
    "eff_converse_labarre": ("Converse–Labarre", "Converse–Labarre"),
    "eff_los_angeles": ("Los Angeles Group", "Los Angeles Group"),
    "eff_seiler_keeney": ("Seiler–Keeney", "Seiler–Keeney"),
    "eff_feld": ("Feld", "Feld"),
    "eff_unity": ("η = 1", "η = 1"),
    "eff_block": ("Block failure", "Blok göçmesi"),
    "gov_efficiency": ("efficiency", "verim"),
    "gov_block": ("block failure", "blok göçmesi"),
    "gs_raft": ("Equivalent raft", "Eşdeğer radye"),
    "gs_vesic": ("Vesić √(Bg/D)", "Vesić √(Bg/D)"),
    "gs_meyerhof": ("Meyerhof SPT", "Meyerhof SPT"),
    "distribution_uniform": ("Uniform (ξ = 0.5)", "Düzgün (ξ = 0.5)"),
    "distribution_triangular": ("Triangular (ξ = 0.67)", "Üçgen (ξ = 0.67)"),
    "model_consolidation": ("consolidation", "konsolidasyon"),
    "model_elastic": ("elastic", "elastik"),
    "model_none": ("—", "—"),
    "modulus_rqd": ("From RQD (Gardner)", "RQD'den (Gardner)"),
    "modulus_gsi": ("From GSI (Hoek & Diederichs)", "GSI'dan (Hoek & Diederichs)"),
    "modulus_direct": ("Entered", "Girilen"),
    "design_mean": ("Mean of the correlations", "Bağıntıların ortalaması"),
    "design_median": ("Median of the correlations", "Bağıntıların medyanı"),
    "design_lower": ("Lowest (longest socket)", "En düşük (en uzun soket)"),
    "design_upper": ("Highest (shortest socket)", "En yüksek (en kısa soket)"),
    "base_design_none": ("None (side only)", "Yok (yalnız yanal)"),
    "base_design_min": ("Lowest of the methods", "Yöntemlerin en düşüğü"),
    "base_design_mean": ("Mean of the methods", "Yöntemlerin ortalaması"),
    "side_rosenberg_journeaux": ("Rosenberg & Journeaux (1976)", "Rosenberg & Journeaux (1976)"),
    "side_horvath_kenney": ("Horvath & Kenney (1979)", "Horvath & Kenney (1979)"),
    "side_meigh_wolski": ("Meigh & Wolski (1979)", "Meigh & Wolski (1979)"),
    "side_williams": ("Williams et al. (1980)", "Williams vd. (1980)"),
    "side_reynolds_kaderabek": ("Reynolds & Kaderabek (1980)", "Reynolds & Kaderabek (1980)"),
    "side_gupton_logan": ("Gupton & Logan (1984)", "Gupton & Logan (1984)"),
    "side_rowe_armitage": ("Rowe & Armitage (1987)", "Rowe & Armitage (1987)"),
    "side_carter_kulhawy": ("Carter & Kulhawy (1988)", "Carter & Kulhawy (1988)"),
    "side_toh": ("Toh et al. (1989)", "Toh vd. (1989)"),
    "side_zhang_einstein": ("Zhang & Einstein (1998)", "Zhang & Einstein (1998)"),
    "side_oneill_reese": ("O'Neill & Reese (1999) / AASHTO", "O'Neill & Reese (1999) / AASHTO"),
    "side_kulhawy_2005": ("Kulhawy et al. (2005)", "Kulhawy vd. (2005)"),
    "base_coates": ("Coates (1967)", "Coates (1967)"),
    "base_rowe_armitage": ("Rowe & Armitage (1987)", "Rowe & Armitage (1987)"),
    "base_carter_kulhawy": ("Carter & Kulhawy (1988), Hoek–Brown",
                            "Carter & Kulhawy (1988), Hoek–Brown"),
    "base_zhang_einstein": ("Zhang & Einstein (1998)", "Zhang & Einstein (1998)"),
    "base_aashto": ("AASHTO / O'Neill & Reese", "AASHTO / O'Neill & Reese"),
    "base_cfem": ("CFEM (Ladanyi & Roy)", "CFEM (Ladanyi & Roy)"),

    # ------------------------------------------------------------------ tables
    "col_name": ("Name", "Ad"),
    "col_thickness": ("t (m)", "t (m)"),
    "col_behaviour": ("Type", "Tür"),
    "col_gamma": ("γ (kN/m³)", "γ (kN/m³)"),
    "col_gamma_sat": ("γsat (kN/m³)", "γdoy (kN/m³)"),
    "col_phi": ("φ' (°)", "φ' (°)"),
    "col_cu": ("cu (kPa)", "cu (kPa)"),
    "col_OCR": ("OCR", "AKO"),
    "col_N60": ("N60", "N60"),
    "col_E": ("E (MPa)", "E (MPa)"),
    "col_nu": ("ν", "ν"),
    "col_Cc": ("Cc", "Cc"),
    "col_Cr": ("Cr", "Cr"),
    "col_e0": ("e0", "e0"),
    "soil_note": ("Layers from the ground surface down. φ' is the effective friction angle, of "
                  "a clay too (β method); cu, OCR, Cc, Cr and e0 belong to clays, N60 to sands "
                  "(0: not measured).",
                  "Tabakalar yüzeyden aşağı doğru. φ' efektif içsel sürtünme açısıdır, kilde de "
                  "(β yöntemi); cu, AKO, Cc, Cr ve e0 killere, N60 kumlara aittir (0: "
                  "ölçülmedi)."),
    "col_param": ("Input", "Girdi"),
    "col_mode": ("Mode", "Mod"),
    "col_min": ("Min", "Min"),
    "col_max": ("Max", "Maks"),
    "col_dist": ("Distribution", "Dağılım"),
    "col_mean": ("Mean", "Ortalama"),
    "col_cov": ("CoV", "CoV"),
    "col_points": ("Points", "Nokta"),
    "mode_range": ("Range", "Aralık"),
    "mode_dist": ("Distribution", "Dağılım"),
    "dist_normal": ("Normal", "Normal"),
    "dist_lognormal": ("Lognormal", "Lognormal"),
    "dist_uniform": ("Uniform", "Düzgün"),

    # ------------------------------------------------------------------ cards
    "card_Q_ult": ("Ultimate capacity", "Nihai taşıma gücü"),
    "card_Q_net": ("Net ultimate capacity", "Net nihai taşıma gücü"),
    "card_Q_all": ("Allowable capacity", "İzin verilebilir taşıma gücü"),
    "card_pile_load": ("Load per pile", "Kazık başına yük"),
    "card_check_pile": ("Single pile", "Tek kazık"),
    "card_check_group": ("Group", "Grup"),
    "card_settlement": ("Group settlement", "Grup oturması"),
    "card_length": ("Required length", "Gerekli boy"),
    "card_weight": ("after W = {W:,.0f} kN", "W = {W:,.0f} kN düşülünce"),
    "card_piles": ("{n} piles, Q = {Q:,.0f} kN", "{n} kazık, Q = {Q:,.0f} kN"),
    "card_tip": ("tip at {z:.2f} m", "uç {z:.2f} m'de"),
    "card_none": ("none", "yok"),
    "card_checks": ("checks", "kontroller"),
    "card_socket_fs": ("Design side shear", "Tasarım yanal sürtünmesi"),
    "card_socket_qb": ("Design base resistance", "Tasarım uç direnci"),
    "card_socket_length": ("Socket length", "Soket boyu"),
    "card_socket_Q_all": ("Allowable capacity", "İzin verilebilir taşıma gücü"),
    "card_socket_check": ("Socket check", "Soket kontrolü"),
    "card_socket_settlement": ("Settlement", "Oturma"),
    "card_at_length": ("at Ls = {Ls:.2f} m", "Ls = {Ls:.2f} m için"),
    "card_base_share": ("{share:.0f} % through the base", "yükün % {share:.0f}'i uçtan"),
    "ok_short": ("OK", "UYGUN"),
    "notok_short": ("NOT OK", "UYGUN DEĞİL"),
    "na_short": ("n/a", "—"),
    "yes": ("yes", "evet"),
    "no": ("no", "hayır"),

    # ------------------------------------------------------------------ results text
    "res_title": ("PILE CAPACITY RESULTS", "KAZIK TAŞIMA GÜCÜ SONUÇLARI"),
    "res_pile": ("Pile: {shape}, D = {D:.2f} m, L = {L:.2f} m, head at {top:.2f} m, tip at "
                 "{tip:.2f} m; {inst}",
                 "Kazık: {shape}, D = {D:.2f} m, L = {L:.2f} m, baş {top:.2f} m'de, uç "
                 "{tip:.2f} m'de; {inst}"),
    "res_area": ("Base area Ab = {A:.4f} m², perimeter p = {p:.3f} m",
                 "Uç alanı Ab = {A:.4f} m², çevre p = {p:.3f} m"),
    "res_group": ("Group: {nx} × {ny} = {n} piles at {sx:.2f} × {sy:.2f} m; Q = {Q:,.0f} kN, "
                  "{Qp:,.0f} kN per pile",
                  "Grup: {nx} × {ny} = {n} kazık, {sx:.2f} × {sy:.2f} m aralıkla; "
                  "Q = {Q:,.0f} kN, kazık başına {Qp:,.0f} kN"),
    "res_water": ("Water table at {zw:.2f} m", "Su tablası {zw:.2f} m'de"),
    "res_zc": ("Critical depth zc = {zc:.2f} m ({ratio:.0f}·D)",
               "Kritik derinlik zc = {zc:.2f} m ({ratio:.0f}·D)"),
    "res_K": ("In sand: K/K0 = {K:.2f}, δ/φ' = {delta:.2f}",
              "Kumda: K/K0 = {K:.2f}, δ/φ' = {delta:.2f}"),
    "res_tip_title": ("BASE RESISTANCE", "UÇ DİRENCİ"),
    "res_tip_layer": ("Tip in '{name}' ({kind}) at {z:.2f} m, σ'v0 = {sv:,.1f} kPa",
                      "Uç '{name}' ({kind}) tabakasında, {z:.2f} m'de, σ'v0 = {sv:,.1f} kPa"),
    "res_shaft_title": ("SHAFT FRICTION", "ÇEVRE SÜRTÜNMESİ"),
    "res_clay_methods": ("Shaft friction by clay method:", "Kil yöntemine göre çevre sürtünmesi:"),
    "res_capacity_title": ("CAPACITY OF A SINGLE PILE", "TEK KAZIĞIN TAŞIMA GÜCÜ"),
    "res_capacity": ("Qs = {Qs:,.0f} kN + Qb = {Qb:,.0f} kN = Qult = {Qu:,.0f} kN",
                     "Qs = {Qs:,.0f} kN + Qb = {Qb:,.0f} kN = Qult = {Qu:,.0f} kN"),
    "res_weight": ("Pile weight W = {W:,.0f} kN (subtracted: {used})",
                   "Kazık ağırlığı W = {W:,.0f} kN (düşüldü: {used})"),
    "res_net": ("Qult,net = {Qn:,.0f} kN, FS = {FS:.2f}, Qall = {Qa:,.0f} kN",
                "Qult,net = {Qn:,.0f} kN, GS = {FS:.2f}, Qall = {Qa:,.0f} kN"),
    "res_group_title": ("PILE GROUP", "KAZIK GRUBU"),
    "res_group_eff": ("η = {eta:.3f}: η·n·Qult = {eta:.3f} · {n} · Qult = {Q:,.0f} kN",
                      "η = {eta:.3f}: η·n·Qult = {eta:.3f} · {n} · Qult = {Q:,.0f} kN"),
    "res_block": ("Block {Bg:.2f} × {Lg:.2f} m: shaft {Qs:,.0f} kN + base {Qb:,.0f} kN = "
                  "{Q:,.0f} kN",
                  "Blok {Bg:.2f} × {Lg:.2f} m: çevre {Qs:,.0f} kN + taban {Qb:,.0f} kN = "
                  "{Q:,.0f} kN"),
    "res_group_capacity": ("Qg,ult = {Q:,.0f} kN ({gov}), Qg,ult − n·W = {Qn:,.0f} kN, "
                           "Qg,all = {Qa:,.0f} kN",
                           "Qg,ult = {Q:,.0f} kN ({gov}), Qg,ult − n·W = {Qn:,.0f} kN, "
                           "Qg,all = {Qa:,.0f} kN"),
    "res_settlement_title": ("SETTLEMENT", "OTURMA"),
    "res_single": ("Single pile (Vesić): s1 = {s1:.2f} + s2 = {s2:.2f} + s3 = {s3:.2f} = "
                   "{s:.2f} mm",
                   "Tek kazık (Vesić): s1 = {s1:.2f} + s2 = {s2:.2f} + s3 = {s3:.2f} = "
                   "{s:.2f} mm"),
    "res_raft": ("Equivalent raft at {z:.2f} m, q = {q:,.1f} kPa: consolidation {c:.1f} + "
                 "elastic {e:.1f} + pile shortening {sh:.1f} = {s:.1f} mm",
                 "Eşdeğer radye {z:.2f} m'de, q = {q:,.1f} kPa: konsolidasyon {c:.1f} + "
                 "elastik {e:.1f} + kazık kısalması {sh:.1f} = {s:.1f} mm"),
    "res_vesic_group": ("Vesić: s·√(Bg/D) = s·√({Bg:.2f}/{D:.2f}) = {s:.1f} mm",
                        "Vesić: s·√(Bg/D) = s·√({Bg:.2f}/{D:.2f}) = {s:.1f} mm"),
    "res_meyerhof_group": ("Meyerhof SPT: N60 = {N:.0f}, I = {I:.2f}, q = {q:,.1f} kPa, "
                           "sg = {s:.1f} mm",
                           "Meyerhof SPT: N60 = {N:.0f}, I = {I:.2f}, q = {q:,.1f} kPa, "
                           "sg = {s:.1f} mm"),
    "res_checks_title": ("CHECKS", "KONTROLLER"),
    "res_check_pile": ("Single pile: FS = {actual:.2f} (required {allowable:.2f}) — {status}",
                       "Tek kazık: GS = {actual:.2f} (gerekli {allowable:.2f}) — {status}"),
    "res_check_group": ("Group: FS = {actual:.2f} (required {allowable:.2f}) — {status}",
                        "Grup: GS = {actual:.2f} (gerekli {allowable:.2f}) — {status}"),
    "res_check_settlement": ("Settlement: {actual:.1f} mm (allowed {allowable:.1f} mm) — "
                             "{status}",
                             "Oturma: {actual:.1f} mm (izin verilen {allowable:.1f} mm) — "
                             "{status}"),
    "res_required_length": ("Required length: L = {L:.2f} m (tip at {z:.2f} m)",
                            "Gerekli boy: L = {L:.2f} m (uç {z:.2f} m'de)"),
    "res_no_length": ("No length down to {hi:.2f} m below the head passes both checks.",
                      "Kazık başından {hi:.2f} m'ye kadar hiçbir boy iki kontrolü sağlamıyor."),
    "res_layers_title": ("SOIL PROFILE", "ZEMİN PROFİLİ"),
    "head_layer": ("Layer", "Tabaka"),
    "head_depth": ("Depth (m)", "Derinlik (m)"),
    "head_sigma": ("σ'v0 (kPa)", "σ'v0 (kPa)"),
    "head_Qs": ("Qs (kN)", "Qs (kN)"),
    "head_shaft_method": ("Shaft method", "Çevre yöntemi"),
    "head_correlation": ("Correlation", "Bağıntı"),
    "head_formula": ("fs (MPa)", "fs (MPa)"),
    "head_fs": ("fs (kPa)", "fs (kPa)"),
    "head_Ls_req": ("Ls needed (m)", "Gereken Ls (m)"),
    "head_Q_all": ("Qall at Ls (kN)", "Ls'de Qall (kN)"),
    "warnings_title": ("Warnings", "Uyarılar"),

    # ------------------------------------------------------------------ socket text
    "sock_title": ("ROCK-SOCKETED PILE", "KAYAYA SOKETLİ KAZIK"),
    "sock_geometry": ("D = {D:.2f} m, head at {top:.2f} m, rock at {rock:.2f} m (overburden "
                      "{Lo:.2f} m), socket Ls = {Ls:.2f} m, Q = {Q:,.0f} kN",
                      "D = {D:.2f} m, baş {top:.2f} m'de, kaya {rock:.2f} m'de (örtü "
                      "{Lo:.2f} m), soket Ls = {Ls:.2f} m, Q = {Q:,.0f} kN"),
    "sock_rock": ("qu = {qu:.1f} MPa (side shear with {qs:.1f} MPa, f'c = {fc:.1f} MPa), "
                  "Em = {Em:,.0f} MPa, Em/Ei = {ratio:.3f}, αE = {aE:.3f}",
                  "qu = {qu:.1f} MPa (yanal sürtünmede {qs:.1f} MPa, f'c = {fc:.1f} MPa), "
                  "Em = {Em:,.0f} MPa, Em/Ei = {ratio:.3f}, αE = {aE:.3f}"),
    "sock_hb": ("Hoek–Brown: GSI = {GSI:.0f}, mi = {mi:.1f}, mb = {mb:.3f}, s = {s:.2e}",
                "Hoek–Brown: GSI = {GSI:.0f}, mi = {mi:.1f}, mb = {mb:.3f}, s = {s:.2e}"),
    "sock_side_title": ("UNIT SIDE SHEAR AND SOCKET LENGTH", "BİRİM YANAL SÜRTÜNME VE SOKET BOYU"),
    "sock_stats": ("{n} correlations in range: mean {mean:,.0f}, median {median:,.0f}, "
                   "{lo:,.0f} – {hi:,.0f} kPa",
                   "Geçerli {n} bağıntı: ortalama {mean:,.0f}, medyan {median:,.0f}, "
                   "{lo:,.0f} – {hi:,.0f} kPa"),
    "sock_weak_note": ("† fitted to weak rock; out of range above qu = {limit:.1f} MPa",
                       "† zayıf kayaya uydurulmuş; qu = {limit:.1f} MPa üstünde geçersiz"),
    "sock_base_title": ("UNIT BASE RESISTANCE", "BİRİM UÇ DİRENCİ"),
    "sock_design_title": ("DESIGN", "TASARIM"),
    "sock_design": ("fs = {fs:,.0f} kPa, qb = {qb:,.2f} MPa, FSside = {FSs:.2f}, "
                    "FSbase = {FSb:.2f}",
                    "fs = {fs:,.0f} kPa, qb = {qb:,.2f} MPa, GSyanal = {FSs:.2f}, "
                    "GSuç = {FSb:.2f}"),
    "sock_length": ("Socket length needed {Ls:.2f} m, minimum {mn:.2f} m → design "
                    "Ls = {Ld:.2f} m",
                    "Gereken soket boyu {Ls:.2f} m, en az {mn:.2f} m → tasarım "
                    "Ls = {Ld:.2f} m"),
    "sock_no_length": ("No socket length carries the load with the design side shear.",
                       "Tasarım yanal sürtünmesiyle yükü taşıyan soket boyu yok."),
    "sock_check": ("At Ls = {Ls:.2f} m: Qs = {Qs:,.0f}, Qb = {Qb:,.0f}, W = {W:,.0f}, "
                   "Qall = {Qa:,.0f} kN against Q = {Q:,.0f} kN (Q/Qall = {u:.2f}) — {status}",
                   "Ls = {Ls:.2f} m'de: Qs = {Qs:,.0f}, Qb = {Qb:,.0f}, W = {W:,.0f}, "
                   "Qall = {Qa:,.0f} kN, Q = {Q:,.0f} kN (Q/Qall = {u:.2f}) — {status}"),
    "sock_settlement_title": ("ELASTIC SETTLEMENT AT Ls = {Ls:.2f} m",
                              "Ls = {Ls:.2f} m İÇİN ELASTİK OTURMA"),
    "sock_shortening": ("Shortening through the overburden: {s:.2f} mm",
                        "Örtü tabakasındaki kısalma: {s:.2f} mm"),
    "sock_rw": ("Randolph & Wroth, side and base: {s:.2f} mm ({share:.0f} % through the base)",
                "Randolph & Wroth, çevre ve uç: {s:.2f} mm (yükün % {share:.0f}'i uçtan)"),
    "sock_rw_side": ("Randolph & Wroth, side only: {s:.2f} mm",
                     "Randolph & Wroth, yalnız çevre: {s:.2f} mm"),
    "sock_vesic": ("Vesić: {s:.2f} mm", "Vesić: {s:.2f} mm"),

    # ------------------------------------------------------------------ figures
    "fig_section": ("Section through the pile group", "Kazık grubu kesiti"),
    "fig_profile": ("Stresses and shaft friction with depth",
                    "Derinlikle gerilmeler ve çevre sürtünmesi"),
    "fig_methods": ("Shaft and base resistance by method", "Yönteme göre çevre ve uç direnci"),
    "fig_length": ("Capacity against pile length", "Kazık boyuna göre taşıma gücü"),
    "fig_group": ("Plan of the group and its efficiency", "Grup planı ve grup verimi"),
    "fig_settlement": ("Settlement of the group", "Grubun oturması"),
    "fig_socket_section": ("Section through the socketed pile", "Soketli kazık kesiti"),
    "fig_socket_side": ("Unit side shear by correlation", "Bağıntılara göre birim yanal sürtünme"),
    "fig_socket_length": ("Socket length by correlation", "Bağıntılara göre soket boyu"),
    "fig_socket_settlement": ("Head settlement against socket length",
                              "Soket boyuna göre kazık başı oturması"),
    "plot_water": ("water table", "su tablası"),
    "plot_tip": ("tip", "uç"),
    "plot_raft": ("equivalent raft", "eşdeğer radye"),
    "plot_stress": ("Stress", "Gerilme"),
    "plot_depth": ("Depth", "Derinlik"),
    "plot_sv_sand": ("σ'v in sand (zc)", "Kumda σ'v (zc)"),
    "plot_load": ("Load", "Yük"),
    "plot_shaft": ("Shaft friction", "Çevre sürtünmesi"),
    "plot_base": ("Base resistance", "Uç direnci"),
    "plot_length": ("Pile length L", "Kazık boyu L"),
    "plot_Q_net": ("Qult,net", "Qult,net"),
    "plot_Q_all": ("Qall", "Qall"),
    "plot_group_per_pile": ("Qg,all / n", "Qg,all / n"),
    "plot_pile_load": ("load per pile", "kazık başına yük"),
    "plot_required": ("required L = {L:.2f} m", "gerekli L = {L:.2f} m"),
    "plot_raft_title": ("Below the raft at {z:.2f} m", "{z:.2f} m'deki radyenin altı"),
    "plot_settlement": ("Settlement", "Oturma"),
    "plot_allowable": ("allowable", "izin verilen"),
    "plot_s_single": ("Single pile", "Tek kazık"),
    "plot_s_raft": ("Equivalent raft", "Eşdeğer radye"),
    "plot_s_vesic": ("Vesić", "Vesić"),
    "plot_s_meyerhof": ("Meyerhof SPT", "Meyerhof SPT"),
    "plot_no_data": ("Nothing to draw.", "Çizilecek bir şey yok."),
    "plot_overburden": ("overburden", "örtü tabakası"),
    "plot_rock": ("rock", "kaya"),
    "plot_design": ("design", "tasarım"),
    "plot_out_of_range": ("outside its range", "geçerlilik aralığı dışında"),
    "plot_design_length": ("design Ls = {Ls:.2f} m", "tasarım Ls = {Ls:.2f} m"),
    "plot_checked_length": ("checked Ls = {Ls:.2f} m", "kontrol edilen Ls = {Ls:.2f} m"),
    "plot_rw": ("Randolph & Wroth, side and base", "Randolph & Wroth, çevre ve uç"),
    "plot_rw_side": ("Randolph & Wroth, side only", "Randolph & Wroth, yalnız çevre"),
    "plot_vesic_socket": ("Vesić", "Vesić"),

    # ------------------------------------------------------------------ actions
    "run_analysis_button": ("▶ Analyse pile", "▶ Kazığı hesapla"),
    "run_socket_button": ("▶ Analyse socket", "▶ Soketi hesapla"),
    "running_analysis": ("Running…", "Hesaplanıyor…"),
    "analysis_complete": ("Analysis complete.", "Analiz tamamlandı."),
    "socket_complete": ("Socket analysed.", "Soket hesaplandı."),
    "report_action": ("Export report…", "Rapor al…"),
    "report_running": ("Writing the report…", "Rapor yazılıyor…"),

    # ------------------------------------------------------------------ study
    "group_study": ("Study options", "Çalışma seçenekleri"),
    "study_method": ("Sampling", "Örnekleme"),
    "study_n": ("Samples", "Örnek sayısı"),
    "study_seed": ("Seed (0: random)", "Tohum (0: rastgele)"),
    "study_note": ("Every sample is a whole pile analysis without the length search.",
                   "Her örnek, boy araması dışında tam bir kazık analizidir."),
    "sampling_oat": ("One at a time", "Tek tek"),
    "sampling_lhs": ("Latin hypercube", "Latin hiperküp"),
    "sampling_mc": ("Monte Carlo", "Monte Carlo"),
    "study_run": ("▶ Run study", "▶ Çalışmayı başlat"),
    "study_cancel": ("Cancel", "İptal"),
    "study_export_csv": ("CSV", "CSV"),
    "study_export_xlsx": ("XLSX", "XLSX"),
    "study_vars_group": ("Study variables", "Çalışma değişkenleri"),
    "study_no_vars": ("Add at least one study variable.",
                      "En az bir çalışma değişkeni ekleyiniz."),
    "study_progress": ("Sample {done} of {total}…", "Örnek {done} / {total}…"),
    "study_done": ("Study complete: {n} samples.", "Çalışma tamamlandı: {n} örnek."),
    "study_cancelled": ("(cancelled)", "(iptal edildi)"),
    "study_failed": ("The study cannot start: {e}", "Çalışma başlatılamadı: {e}"),
    "study_no_data": ("No study results yet.", "Henüz çalışma sonucu yok."),
    "study_table_note": ("The first 500 samples are shown; the export has them all.",
                         "İlk 500 örnek gösterilir; dışa aktarılan dosyada hepsi vardır."),
    "study_fig_oat": ("One-at-a-time sweep", "Tek tek tarama"),
    "study_fig_hist": ("Distribution of the output", "Çıktının dağılımı"),
    "study_fig_scatter": ("Output against the inputs", "Girdilere göre çıktı"),
    "study_fig_tornado": ("Sensitivity", "Duyarlılık"),
    "out_Q_ult": ("Qult (kN)", "Qult (kN)"),
    "out_Q_ult_net": ("Qult,net (kN)", "Qult,net (kN)"),
    "out_Q_all": ("Qall (kN)", "Qall (kN)"),
    "out_FS": ("FS, single pile", "GS, tek kazık"),
    "out_utilisation": ("Utilisation, single pile", "Kullanım, tek kazık"),
    "out_Qg_all": ("Qg,all (kN)", "Qg,all (kN)"),
    "out_FS_group": ("FS, group", "GS, grup"),
    "out_utilisation_group": ("Utilisation, group", "Kullanım, grup"),
    "out_settlement": ("Settlement (mm)", "Oturma (mm)"),
    "ls_pile": ("Single pile", "Tek kazık"),
    "ls_group": ("Group", "Grup"),
    "ls_settlement": ("Settlement", "Oturma"),
    "st_title": ("STUDY RESULTS", "ÇALIŞMA SONUÇLARI"),
    "st_info": ("Method: {method}; samples: {n}; successful: {ok}",
                "Yöntem: {method}; örnek: {n}; başarılı: {ok}"),
    "st_stats_title": ("Statistics of the outputs", "Çıktıların istatistikleri"),
    "st_rel_title": ("Probability of failure", "Göçme olasılığı"),
    "st_rel_line": ("{name}: {k} of {n}, P = {pf:.3g} (95 % CI {lo:.3g} – {hi:.3g}), β = {beta}",
                    "{name}: {n} örnekte {k}, P = {pf:.3g} (%95 GA {lo:.3g} – {hi:.3g}), "
                    "β = {beta}"),
    "st_sens_title": ("Sensitivity of the factor of safety (Spearman ρ)",
                      "Güvenlik sayısının duyarlılığı (Spearman ρ)"),
    "st_no_sens": ("Sensitivities need at least three samples of a sampled variable.",
                   "Duyarlılık için örneklenen değişkenin en az üç örneği gerekir."),
    "st_mean": ("mean", "ort."),
    "st_std": ("std", "std"),

    # ------------------------------------------------------------------ variable names
    "var_D": ("D", "D"),
    "var_L": ("L", "L"),
    "var_top": ("head depth", "baş derinliği"),
    "var_Q": ("Q", "Q"),
    "var_sx": ("sx", "sx"),
    "var_sy": ("sy", "sy"),
    "var_depth": ("water table", "su tablası"),
    "var_delta_ratio": ("δ/φ'", "δ/φ'"),
    "var_thickness": ("t", "t"),
    "var_gamma": ("γ", "γ"),
    "var_gamma_sat": ("γsat", "γdoy"),
    "var_phi": ("φ'", "φ'"),
    "var_cu": ("cu", "cu"),
    "var_OCR": ("OCR", "AKO"),
    "var_N60": ("N60", "N60"),
    "var_E": ("E", "E"),
    "var_nu": ("ν", "ν"),
    "var_Cc": ("Cc", "Cc"),
    "var_Cr": ("Cr", "Cr"),
    "var_e0": ("e0", "e0"),
    "grp_pile": ("Pile", "Kazık"),
    "grp_loading": ("Load", "Yük"),
    "grp_group": ("Group", "Grup"),
    "grp_water": ("Groundwater", "Yeraltı suyu"),
    "grp_options": ("Methods", "Yöntemler"),
    "grp_seismic": ("Earthquake", "Deprem"),
    "var_E_V": ("V", "V"),
    "var_E_M_B": ("M_B", "M_B"),
    "var_E_M_L": ("M_L", "M_L"),
    "var_E_cyclic": ("ζ", "ζ"),

    # ------------------------------------------------------------------ seismic load case
    "group_seismic": ("Seismic load case", "Deprem yükleme durumu"),
    "seismic_enabled_label": ("Check the seismic load case", "Deprem durumunu kontrol et"),
    "V_E_label": ("Vertical load V (negative: uplift)", "Düşey yük V (negatif: çekme)"),
    "M_B_label": ("Moment M_B (loads vary along B)", "Moment M_B (yük B yönünde değişir)"),
    "M_L_label": ("Moment M_L (loads vary along L)", "Moment M_L (yük L yönünde değişir)"),
    "tension_sand_label": ("Shaft friction in tension / compression, sand",
                           "Çekme / basınç çevre sürtünmesi oranı, kum"),
    "tension_clay_label": ("Shaft friction in tension / compression, clay",
                           "Çekme / basınç çevre sürtünmesi oranı, kil"),
    "cyclic_label": ("Cyclic reduction of the shaft friction ζ",
                     "Tekrarlı yükte çevre sürtünmesi azaltması ζ"),
    "FS_E_c_label": ("Factor of safety, compression", "Güvenlik sayısı, basınç"),
    "FS_E_t_label": ("Factor of safety, uplift", "Güvenlik sayısı, çekme"),
    "seismic_note": ("The seismic combination at the underside of the cap, from the "
                     "structural analysis. The rigid cap shares it among the piles: "
                     "P = V/n + M_B·x/Σx² + M_L·y/Σy². A pile in tension is held by its shaft "
                     "friction in tension and its own weight.",
                     "Yapı analizinden gelen deprem kombinasyonu, başlık altında. Rijit "
                     "başlık bunu kazıklara paylaştırır: P = V/n + M_B·x/Σx² + M_L·y/Σy². "
                     "Çekmedeki kazığı, çekmedeki çevre sürtünmesi ve kendi ağırlığı tutar."),
    "card_seismic_compression": ("Seismic compression", "Deprem basıncı"),
    "card_seismic_tension": ("Seismic uplift", "Deprem çekmesi"),
    "card_no_tension": ("no tension", "çekme yok"),
    "res_seismic_title": ("SEISMIC LOAD CASE", "DEPREM YÜKLEME DURUMU"),
    "res_seismic_loads": ("V = {V:,.0f} kN, M_B = {MB:,.0f} kN·m, M_L = {ML:,.0f} kN·m: pile "
                          "loads from {pmin:,.0f} to {pmax:,.0f} kN",
                          "V = {V:,.0f} kN, M_B = {MB:,.0f} kN·m, M_L = {ML:,.0f} kN·m: kazık "
                          "yükleri {pmin:,.0f} ile {pmax:,.0f} kN arasında"),
    "res_seismic_compression": ("Compression: Qult,net / FS = {Qn:,.0f} / {FS:.2f} = "
                                "{Qa:,.0f} kN against Pmax = {P:,.0f} kN",
                                "Basınç: Qult,net / GS = {Qn:,.0f} / {FS:.2f} = {Qa:,.0f} kN, "
                                "Pmax = {P:,.0f} kN"),
    "res_seismic_uplift": ("Uplift: λt = {ts:.2f} (sand), {tc:.2f} (clay), ζ = {cy:.2f}; "
                           "Qs,t = {Qs:,.0f} kN, W = {W:,.0f} kN, Tall = Qs,t / {FS:.2f} + W = "
                           "{Ta:,.0f} kN",
                           "Çekme: λt = {ts:.2f} (kum), {tc:.2f} (kil), ζ = {cy:.2f}; "
                           "Qs,t = {Qs:,.0f} kN, W = {W:,.0f} kN, Tall = Qs,t / {FS:.2f} + W = "
                           "{Ta:,.0f} kN"),
    "res_seismic_tension": ("Largest tension T = {T:,.0f} kN, {n} piles in tension",
                            "En büyük çekme T = {T:,.0f} kN, çekmede {n} kazık"),
    "res_seismic_no_tension": ("No pile is in tension.", "Çekmede kazık yok."),
    "res_seismic_block": ("Block {Bg:.2f} × {Lg:.2f} m lifted as a whole: shear {Qs:,.0f} kN, "
                          "weight {W:,.0f} kN, Tall = {Ta:,.0f} kN against T = {T:,.0f} kN",
                          "{Bg:.2f} × {Lg:.2f} m blok bütün olarak kalkıyor: kesme "
                          "{Qs:,.0f} kN, ağırlık {W:,.0f} kN, Tall = {Ta:,.0f} kN, "
                          "T = {T:,.0f} kN"),
    "res_check_seismic_compression": ("Seismic compression: FS = {actual:.2f} (required "
                                      "{allowable:.2f}) — {status}",
                                      "Deprem basıncı: GS = {actual:.2f} (gerekli "
                                      "{allowable:.2f}) — {status}"),
    "res_check_seismic_tension": ("Seismic uplift: FS on Qs,t = {actual:.2f} (required "
                                  "{allowable:.2f}) — {status}",
                                  "Deprem çekmesi: Qs,t üzerinde GS = {actual:.2f} (gerekli "
                                  "{allowable:.2f}) — {status}"),
    "res_check_seismic_group_tension": ("Seismic block uplift: FS = {actual:.2f} (required "
                                        "{allowable:.2f}) — {status}",
                                        "Deprem blok çekmesi: GS = {actual:.2f} (gerekli "
                                        "{allowable:.2f}) — {status}"),
    "warn_seismic_single_moment": ("A single pile cannot share a moment through its cap; the "
                                   "seismic moments were left out.",
                                   "Tek kazık momenti başlık üzerinden paylaştıramaz; deprem "
                                   "momentleri hesaba katılmadı."),
    "warn_seismic_tension": ("In the seismic case {n} piles are in tension, the largest pull "
                             "T = {T:,.0f} kN: the reinforcement must carry it down the pile "
                             "and into the cap.",
                             "Deprem durumunda {n} kazık çekmede, en büyük çekme "
                             "T = {T:,.0f} kN: donatı bunu kazık boyunca ve başlığa "
                             "aktarabilmelidir."),
    "fig_seismic": ("Seismic loads on the piles", "Deprem durumunda kazık yükleri"),
    "plot_no_seismic": ("The seismic load case is off.", "Deprem durumu kapalı."),
    "plot_compression": ("compression", "basınç"),
    "plot_tension": ("tension", "çekme"),
    "plot_piles_sorted": ("piles, from the most pulled to the most pushed",
                          "kazıklar, en çok çekmeden en çok basınca"),
    "plot_pile_force": ("Pile load", "Kazık yükü"),
    "out_T_pile": ("Largest tension (kN)", "En büyük çekme (kN)"),
    "out_utilisation_seismic": ("Utilisation, seismic", "Kullanım, deprem"),
    "ls_seismic": ("Seismic", "Deprem"),
}

TRANSLATIONS = {
    "en": {key: pair[0] for key, pair in ENTRIES.items()},
    "tr": {key: pair[1] for key, pair in ENTRIES.items()},
}


def t(lang: str, key: str, **params) -> str:
    """One text in one language, formatted; the key itself if it is unknown."""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    return text.format(**params) if params else text


def warning_text(lang: str, warning) -> str:
    """An engine warning, (key, params), as a sentence."""
    key, params = warning
    return t(lang, key, **params)
