// Source de vérité unique du texte d'avertissement côté frontend.
// Le pendant backend vit dans app/services/disclaimer.py (rapports PDF) —
// garder les deux formulations alignées (exposition réglementaire AMF/SEC/MiFID).
export const DISCLAIMER_HEADING = 'Avertissement'

export const DISCLAIMER_TEXT =
  'Ce système produit de la recherche éducative — pas un conseil financier. ' +
  'Investir comporte un risque de perte en capital.'

// Variante compacte affichée adjacente à un verdict actionnable (E9-S1).
export const VERDICT_DISCLAIMER_TEXT =
  'Recherche éducative — pas un conseil en placement.'
