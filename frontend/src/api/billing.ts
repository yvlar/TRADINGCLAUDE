import { apiClient } from './client'

interface CheckoutResponse {
  checkout_url: string
}

interface PortalResponse {
  portal_url: string
}

/** Crée une session de checkout Stripe pour le plan donné et retourne son URL. */
export async function createCheckout(plan: string): Promise<string> {
  const res = await apiClient.request<CheckoutResponse>('/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({ plan }),
  })
  return res.checkout_url
}

/** Ouvre le Billing Portal Stripe du tenant courant et retourne son URL. */
export async function openPortal(): Promise<string> {
  const res = await apiClient.request<PortalResponse>('/billing/portal', {
    method: 'POST',
  })
  return res.portal_url
}
