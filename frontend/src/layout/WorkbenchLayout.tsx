import { NavLink, Outlet } from 'react-router-dom'

const linkCls = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'active' : undefined

export function WorkbenchLayout() {
  return (
    <div className="workbench">
      <aside className="sidebar">
        <div className="sidebar-brand">Pricing Simulator</div>
        <nav>
          <NavLink to="/" end className={linkCls}>
            Scenario builder
          </NavLink>
          <NavLink to="/validation" className={linkCls}>
            Validation workspace
          </NavLink>
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
