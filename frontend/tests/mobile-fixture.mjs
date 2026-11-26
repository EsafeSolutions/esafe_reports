// Local browser QA only. Values are fixtures, never used by the production app.
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const publicDir = path.join(root, 'lumen_reports/public')
export const fixture = {
  connected: true,
  denied: false,
  offline: false,
  preferences: null,
  requests: [],
}
const status = {
  contract: 3,
  product: 'Esafe BLABS',
  reports_api: true,
  pos_installed: true,
  can_read_source: true,
  dashboard_exists: true,
  can_view: true,
  can_create: true,
  reason: null,
  license: 'licensed',
  slug: 'lumenpos-sales',
  url: '/lumen/dashboard/lumenpos-sales',
  embed_url: '/lumen/embed/lumenpos-sales',
}
const definitions = [
  ['net_sales', 'Net Sales', 'Number Card'],
  ['invoices', 'Invoices', 'Number Card'],
  ['avg_basket', 'Average Basket', 'Number Card'],
  ['returns', 'Returns', 'Number Card'],
  ['sales_by_day', 'Sales by Day', 'Line Chart'],
  ['by_outlet', 'Sales by Outlet', 'Horizontal Bar'],
  ['payment_mix', 'Payment Mix', 'Donut Chart'],
  ['top_items', 'Top Items', 'Horizontal Bar'],
]
const dashboard = {
  name: 'POS Sales',
  title: 'POS Sales',
  slug: 'lumenpos-sales',
  auto_refresh: true,
  can_edit: true,
  layout: [],
  filters: [
    {
      name: 'posting_date',
      fieldtype: 'Date Range',
      label: 'Date',
      default: 'this_month',
    },
    {
      name: 'pos_profile',
      fieldtype: 'Link',
      label: 'Outlet',
      link_doctype: 'POS Profile',
    },
  ],
  widgets: definitions.map(([widget_id, title, widget_type]) => ({
    widget_id,
    title,
    widget_type,
    style: {},
    linked_filters: {
      posting_date: 'posting_date',
      pos_profile: 'pos_profile',
    },
    query: {
      doctype: 'POS Invoice',
      aggregate: { function: 'sum', field: 'grand_total' },
      ...(widget_type !== 'Number Card'
        ? {
            group_by: {
              field:
                widget_id === 'sales_by_day' ? 'posting_date' : 'pos_profile',
              ...(widget_id === 'sales_by_day' ? { time_grain: 'day' } : {}),
            },
          }
        : {}),
    },
  })),
}
const mime = {
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.webmanifest': 'application/manifest+json',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.html': 'text/html',
}

export function startFixtureServer(port = 0) {
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://localhost')
      if (url.pathname === '/socket.io/') {
        res.writeHead(503)
        res.end()
        return
      }
      if (url.pathname === '/api/method/lumen_reports.pwa.service_worker') {
        const { version } = JSON.parse(
          await readFile(path.join(publicDir, 'frontend/version.json'), 'utf8'),
        )
        res.writeHead(200, {
          'Content-Type': 'application/javascript',
          'Service-Worker-Allowed': '/esafe-report/',
          'Cache-Control': 'no-store',
        })
        res.end(
          (await readFile(path.join(publicDir, 'pwa/sw.js'), 'utf8')).replace(
            '__LUMEN_BUILD__',
            version,
          ),
        )
        return
      }
      if (url.pathname.startsWith('/api/method/')) {
        let data = Object.fromEntries(url.searchParams)
        if (req.method === 'POST') {
          let body = ''
          for await (const part of req) body += part
          data = {
            ...data,
            ...(body.startsWith('{')
              ? JSON.parse(body)
              : Object.fromEntries(new URLSearchParams(body))),
          }
        }
        const method = url.pathname.slice('/api/method/'.length)
        fixture.requests.push({
          method,
          verb: req.method,
          data,
          csrf: req.headers['x-frappe-csrf-token'],
        })
        res.setHeader('Content-Type', 'application/json')
        if (fixture.offline) {
          res.writeHead(503)
          res.end('{}')
          return
        }
        if (
          fixture.denied &&
          /get_dashboard|run_widget|get_context/.test(method)
        ) {
          res.writeHead(403)
          res.end('{}')
          return
        }
        let message = {}
        if (method === 'lumen_reports.mobile.get_context')
          message = {
            connection: {
              ...status,
              ...(fixture.connected
                ? {}
                : {
                    dashboard_exists: false,
                    can_view: false,
                    reason: 'not_set_up',
                  }),
            },
            currency: 'LKR',
            user: 'Administrator',
          }
        else if (method.endsWith('get_status')) message = status
        else if (method.endsWith('ensure_dashboard')) {
          fixture.connected = true
          message = { status: 'ready', created: true }
        } else if (method.endsWith('get_dashboard')) message = dashboard
        else if (method.endsWith('get_dashboards'))
          message = { dashboards: [], can_create: true }
        else if (method.endsWith('get_link_options'))
          message = ['SHOWROOM · Esafe', 'CITY CENTRE · Esafe']
            .filter((label) =>
              label.toLowerCase().includes((data.txt || '').toLowerCase()),
            )
            .map((label) => ({ value: label, label }))
        else if (method.endsWith('run_widget')) {
          const filters =
            typeof data.filter_values === 'string'
              ? JSON.parse(data.filter_values)
              : data.filter_values || {}
          const factor = filters.pos_profile ? 0.5 : 1
          const numbers = {
            net_sales: 284650,
            invoices: 128,
            avg_basket: 2223.83,
            returns: -4500,
          }
          if (data.widget_id in numbers)
            message = {
              result_type: 'number',
              value: numbers[data.widget_id] * factor,
            }
          else if (data.widget_id === 'sales_by_day')
            message = {
              result_type: 'series',
              labels: [
                '2026-11-20',
                '2026-11-21',
                '2026-11-22',
                '2026-11-23',
                '2026-11-24',
                '2026-11-25',
                '2026-11-26',
              ],
              values: [
                65000, 125000, 160000, 140000, 200000, 260000, 230000,
              ].map((n) => n * factor),
            }
          else
            message = {
              result_type: 'series',
              labels:
                data.widget_id === 'payment_mix'
                  ? ['Cash', 'Card', 'Bank transfer']
                  : ['Showroom', 'City centre', 'Online'],
              values: [160000, 84000, 40650].map((n) => n * factor),
            }
        } else if (method.endsWith('notifications.get_settings'))
          message = {
            configured: true,
            public_key: 'B' + 'A'.repeat(86),
            device: fixture.preferences,
          }
        else if (method.endsWith('notifications.get_feed')) message = []
        else if (method.endsWith('notifications.subscribe')) {
          fixture.preferences = {
            enabled: true,
            ...(typeof data.preferences === 'string'
              ? JSON.parse(data.preferences)
              : data.preferences),
          }
          message = fixture.preferences
        } else if (method.endsWith('notifications.unsubscribe')) {
          fixture.preferences = null
          message = { enabled: false }
        } else if (method.endsWith('notifications.send_test'))
          message = { queued: true }
        else if (method.endsWith('get_license_notice')) message = { notice: '' }
        res.end(JSON.stringify({ message }))
        return
      }
      if (url.pathname.startsWith('/assets/lumen_reports/')) {
        const file = path.resolve(
          publicDir,
          decodeURIComponent(
            url.pathname.slice('/assets/lumen_reports/'.length),
          ),
        )
        if (!file.startsWith(publicDir + path.sep)) {
          res.writeHead(403)
          res.end()
          return
        }
        res.setHeader(
          'Content-Type',
          mime[path.extname(file)] || 'application/octet-stream',
        )
        res.end(await readFile(file))
        return
      }
      let html = await readFile(
        path.join(root, 'lumen_reports/www/lumen.html'),
        'utf8',
      )
      html = html.replace(
        /<script>\s*\{% for key in boot %\}[\s\S]*?<\/script>/,
        '<script>window.csrf_token="fixture-csrf";window.site_name="osaka.cloud.esafe.lk";window.lumen_brand={organization:"Osaka City",can_manage:true};</script>',
      )
      res.setHeader('Content-Type', 'text/html')
      res.end(html)
    } catch (error) {
      console.error(error)
      res.writeHead(500)
      res.end('Fixture error')
    }
  })
  return new Promise((resolve) =>
    server.listen(port, '127.0.0.1', () => resolve(server)),
  )
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const server = await startFixtureServer(
    Number(process.env.MOBILE_PREVIEW_PORT || 4173),
  )
  console.log(
    `Mobile fixture preview: http://127.0.0.1:${server.address().port}/esafe-report/mobile`,
  )
}
