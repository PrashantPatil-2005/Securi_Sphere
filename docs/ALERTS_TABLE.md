# Alerts table — virtualization & keyboard nav

Enterprise SOC alert triage on `/alerts`.

## Virtualized table

Uses `VirtualDataTable` (`@tanstack/react-virtual`) — only visible rows render, keeping performance stable at 50+ alerts per page.

Columns: severity, title, status, host, created time. Checkbox column for analysts/admins.

## Bulk actions

Select rows (or **Select all on page**), then:

| Action | Effect |
|--------|--------|
| Investigate | `status=investigating` |
| Assign to me | `status=investigating` + `assigned_to` current user |
| Resolve | `status=resolved` |
| Close | `status=closed` |

API: `PATCH /api/v1/alerts/bulk` (max 500 IDs).

## Keyboard shortcuts

Desktop only (when not focused in an input):

| Key | Action |
|-----|--------|
| `j` / `↓` | Next row |
| `k` / `↑` | Previous row |
| `Enter` | Open investigation pane |
| `Space` | Toggle row selection |
| `i` | Investigate selected (or focused row) |
| `r` | Resolve selected (or focused row) |

## Mobile

Card layout below 768px with the same selection and investigation drawer.
