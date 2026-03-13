FISH_SPECIES = [
    "Kapor",
    "Amur",
    "Šťuka",
    "Zubáč",
    "Sumec",
    "Ostriež",
    "Pstruh",
    "Lipeň",
    "Jelec",
    "Plotica",
    "Pleskáč",
    "Tolstolobik",
    "Karas",
    "Lín",
    "Úhor",
]

FISH_SPECIES_CHOICES = [("", "Vyber druh ryby")] + [
    (species, species) for species in FISH_SPECIES
]