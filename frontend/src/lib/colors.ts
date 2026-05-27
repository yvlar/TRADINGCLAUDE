// Couleurs des graphiques recharts. recharts applique les couleurs comme attributs
// SVG (stroke/fill), qui ne résolvent pas `var(--token)` — on reflète donc ici les mêmes
// valeurs HSL que les tokens sémantiques de `index.css` (--bull/--bear/--neutral) afin de
// garder une source unique. Toute modification d'un token doit être répercutée ici.
export const CHART = {
  bull: 'hsl(142 71% 58%)', // = --bull (positif / FORT)
  bear: 'hsl(0 89% 71%)', // = --bear (négatif / FAIBLE)
  neutral: 'hsl(38 92% 56%)', // = --neutral (modéré)
  grid: 'hsl(215 25% 27%)', // lignes de grille
  axis: 'hsl(215 20% 65%)', // graduations / texte d'axe (= muted-foreground)
  line: 'hsl(215 20% 65%)', // série neutre par défaut
  tooltipBg: 'hsl(222 47% 7%)', // = --background
  tooltipBorder: 'hsl(215 25% 27%)',
  cursor: 'hsl(217 33% 17%)', // surbrillance survol barre
} as const

// Palette catégorielle pour les séries multiples (comparaison multi-tickers, camembert coûts).
export const SERIES = [
  'hsl(213 94% 68%)', // bleu
  'hsl(142 71% 58%)', // bull
  'hsl(27 96% 61%)', // orange
  'hsl(270 95% 75%)', // violet
  'hsl(0 89% 71%)', // bear
  'hsl(48 96% 53%)', // jaune
  'hsl(172 66% 50%)', // sarcelle
  'hsl(330 81% 70%)', // rose
  'hsl(83 78% 55%)', // lime
  'hsl(199 89% 60%)', // ciel
] as const
