import type { User } from '@supabase/supabase-js'
import { UserProfile } from './Auth'

interface SidebarProps {
  user: User
  currentView: 'evaluate' | 'dashboard'
  sidebarCollapsed: boolean
  onViewChange: (view: 'evaluate' | 'dashboard') => void
  onToggleSidebar: () => void
  onSignOut: () => void
}

export function Sidebar({ 
  user, 
  currentView, 
  sidebarCollapsed, 
  onViewChange, 
  onToggleSidebar, 
  onSignOut 
}: SidebarProps) {
  return (
    <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!sidebarCollapsed && <h1>Codebase Evaluator</h1>}
        <button 
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? '»' : '←'}
        </button>
      </div>
      
      <nav className="sidebar-nav">
        <button 
          className={`nav-item ${currentView === 'evaluate' ? 'active' : ''}`}
          onClick={() => onViewChange('evaluate')}
        >
          <span className="nav-icon">📊</span>
          {!sidebarCollapsed && <span>Evaluate Code</span>}
        </button>
        <button 
          className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
          onClick={() => onViewChange('dashboard')}
        >
          <span className="nav-icon">📈</span>
          {!sidebarCollapsed && <span>Dashboard</span>}
        </button>
      </nav>
      
      {!sidebarCollapsed && (
        <div className="sidebar-footer">
          <UserProfile user={user} onSignOut={onSignOut} />
        </div>
      )}
    </aside>
  )
}