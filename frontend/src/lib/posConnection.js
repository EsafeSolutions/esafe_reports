// ESAFE POS uses the existing reporting contract on the same Frappe site.
export const STATUS_METHOD = 'lumen_reports.integrations.lumenpos.get_status'
export const SETUP_METHOD = 'lumen_reports.integrations.lumenpos.ensure_dashboard'

export function connectionState(status) {
  if (!status) return 'loading'
  if (!status.pos_installed) return 'pos_missing'
  if (status.reason && status.reason !== 'not_set_up') return status.reason
  if (!status.can_read_source) return 'needs_data_access'
  if (!status.dashboard_exists) {
    if (status.license === 'expired') return 'license_expired'
    return status.can_create ? 'not_set_up' : 'needs_setup_access'
  }
  return status.can_view ? 'ready' : 'not_in_audience'
}

export const CONNECTION_MESSAGES = {
  loading: ['Checking your connection', 'Reading the reporting status from this site.'],
  ready: ['Your sales dashboard is ready', 'Open Insights → Sales dashboard in ESAFE POS to see your live reports.'],
  pos_missing: ['Install ESAFE POS on this site', 'ESAFE REPORT connects to ESAFE POS installed on the same Frappe site. Ask your site administrator to install the POS app here.'],
  needs_erpnext: ['ERPNext is required', 'Install ERPNext on this site to report on POS invoices.'],
  frontend_missing: ['The report interface needs a build', 'Ask your site administrator to build the reporting app, then check again.'],
  not_set_up: ['Connect your sales dashboard', 'Create the dashboard once, then open it directly from Insights in ESAFE POS.'],
  needs_role: ['Reporting access is required', 'Ask your administrator for restricted ESAFE REPORT access and POS manager access.'],
  not_in_audience: ['This dashboard is restricted', 'Ask the dashboard owner to include your user or POS manager role in its audience.'],
  needs_data_access: ['POS invoice access is required', 'Ask your administrator for read access to POS Invoice and the linked records used by the dashboard.'],
  needs_setup_access: ['An administrator needs to set up reports', 'Ask a System Manager or an ESAFE REPORT builder or manager to create the sales dashboard.'],
  license_expired: ['The reporting subscription has expired', 'Renew the reporting subscription before creating the dashboard. Existing dashboards remain readable.'],
}

export async function readConnection() {
  const response = await fetch(`/api/method/${STATUS_METHOD}`, {
    method: 'GET', credentials: 'same-origin', headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new Error('Could not check the connection. Check that you are signed in and try again.')
  const body = await response.json()
  if (!body.message || body.message.contract !== 3 || !('pos_installed' in body.message)) {
    throw new Error('Update ESAFE REPORT on this site, then check the connection again.')
  }
  return body.message
}
