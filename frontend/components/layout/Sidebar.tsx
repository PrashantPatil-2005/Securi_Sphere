"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  LayoutDashboard,
  Server,
  Activity,
  Bell,
  ShieldAlert,
  Search,
  BarChart3,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Moon,
  Sun,
  User,
  Network,
  Target,
  Clock,
  AlertTriangle,
  FlaskConical,
  ScrollText,
  Shield,
  Gauge,
} from "lucide-react";
import { logoutApi } from "@/lib/api";
import { useUser, canAccessRoute } from "@/lib/hooks/useUser";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { useWsConnected } from "@/lib/websocket";
import { cn } from "@/lib/utils/cn";
import { BrandLogo } from "./BrandLogo";

const MIN_WIDTH = 200;
const MAX_WIDTH = 320;
const COLLAPSED_WIDTH = 56;
const DEFAULT_WIDTH = 240;

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Overview",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/metrics", label: "Metrics", icon: Gauge },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/hosts", label: "Hosts", icon: Server },
      { href: "/events", label: "Events", icon: Activity },
      { href: "/alerts", label: "Alerts", icon: Bell },
      { href: "/offenses", label: "Offenses", icon: ShieldAlert },
      { href: "/incidents", label: "Investigations", icon: AlertTriangle },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/mitre", label: "MITRE ATT&CK", icon: Target },
      { href: "/timeline", label: "Timeline", icon: Clock },
      { href: "/network", label: "Network", icon: Network },
      { href: "/search", label: "Search", icon: Search },
    ],
  },
  {
    title: "Management",
    items: [
      { href: "/rules", label: "Detection Rules", icon: Shield },
      { href: "/reports", label: "Reports", icon: FileText },
      { href: "/audit", label: "Audit Log", icon: ScrollText },
      { href: "/simulation", label: "Simulation", icon: FlaskConical },
      { href: "/system", label: "System Health", icon: Activity },
    ],
  },
];

const NavLink = memo(function NavLink({
  href,
  label,
  icon: Icon,
  active,
  collapsed,
  onNavigate,
}: NavItem & { active: boolean; collapsed: boolean; onNavigate?: () => void }) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={cn("nav-link", active ? "nav-link-active" : "nav-link-idle", collapsed && "justify-center px-2")}
      title={collapsed ? label : undefined}
    >
      <Icon className="w-4 h-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );
});

interface SidebarProps {
  className?: string;
  drawer?: boolean;
  onClose?: () => void;
}

export function Sidebar({ className, drawer = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const connected = useWsConnected();
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const effectiveWidth = drawer ? DEFAULT_WIDTH : collapsed ? COLLAPSED_WIDTH : width;
  const isCollapsed = drawer ? false : collapsed;
  const handleNavigate = drawer ? onClose : undefined;

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (collapsed) return;
    e.preventDefault();
    setIsDragging(true);
    dragRef.current = { startX: e.clientX, startWidth: width };
  }, [collapsed, width]);

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const delta = e.clientX - dragRef.current.startX;
      setWidth(Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, dragRef.current.startWidth + delta)));
    };
    const onUp = () => {
      setIsDragging(false);
      dragRef.current = null;
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
  }, [isDragging]);

  const { data: user } = useUser();
  const role = user?.role?.name;

  const logout = useCallback(async () => {
    await logoutApi();
    router.push("/login");
  }, [router]);

  const filteredSections = useMemo(
    () =>
      navSections
        .map((section) => ({
          ...section,
          items: section.items.filter((item) => canAccessRoute(role, item.href)),
        }))
        .filter((s) => s.items.length > 0),
    [role],
  );

  return (
    <aside
      style={{ width: effectiveWidth }}
      className={cn(
        "relative flex flex-col shrink-0 glass-nav border-r h-screen sticky top-0",
        !isDragging && !drawer && "transition-[width] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]",
        className,
      )}
    >
      {/* Brand */}
      <div className={cn("px-4 py-3.5 border-b border-border-subtle", isCollapsed && "px-2")}>
        <BrandLogo collapsed={isCollapsed} />
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-4 overflow-y-auto overflow-x-hidden">
        {filteredSections.map((section) => (
          <div key={section.title}>
            {!isCollapsed && (
              <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-muted/70">
                {section.title}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.href}
                  {...item}
                  active={pathname === item.href}
                  collapsed={isCollapsed}
                  onNavigate={handleNavigate}
                />
              ))}
            </div>
          </div>
        ))}
        {!isCollapsed && (
          <div>
            <p className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-muted/70">System</p>
            <NavLink href="/settings" label="Settings" icon={Settings} active={pathname.startsWith("/settings")} collapsed={false} onNavigate={handleNavigate} />
            <NavLink href="/profile" label="Profile" icon={User} active={pathname.startsWith("/profile")} collapsed={false} onNavigate={handleNavigate} />
          </div>
        )}
      </nav>

      {/* Bottom section */}
      <div className="p-2 border-t border-border-subtle space-y-1">
        {!isCollapsed && (
          <div className="px-3 py-2 text-[11px] text-muted flex items-center gap-2">
            <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", connected ? "bg-success" : "bg-danger")} />
            {connected ? "Live feed connected" : "Reconnecting…"}
          </div>
        )}
        <button
          onClick={toggleTheme}
          className={cn("nav-link nav-link-idle w-full", isCollapsed && "justify-center px-2")}
          title={isCollapsed ? (theme === "dark" ? "Light mode" : "Dark mode") : undefined}
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          {!isCollapsed && <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>}
        </button>
        <button
          onClick={logout}
          className={cn("nav-link nav-link-idle w-full text-danger/80 hover:text-danger", isCollapsed && "justify-center px-2")}
          title={isCollapsed ? "Sign out" : undefined}
        >
          <LogOut className="w-4 h-4" />
          {!isCollapsed && <span>Sign out</span>}
        </button>
      </div>

      {/* Collapse toggle */}
      {!drawer && (
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="absolute -right-3 top-16 w-6 h-6 rounded-full bg-card border border-border-subtle flex items-center justify-center text-muted hover:text-foreground hover:border-border transition-colors z-10 shadow-sm"
        aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {isCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
      )}

      {/* Resize handle */}
      {!isCollapsed && !drawer && (
        <div
          onMouseDown={handleMouseDown}
          className={cn(
            "absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-accent/30 transition-colors",
            isDragging && "bg-accent/50",
          )}
          aria-hidden
        />
      )}
    </aside>
  );
}
