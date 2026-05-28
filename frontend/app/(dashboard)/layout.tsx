"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, Server, Users, GitBranch, BarChart3,
  Settings, FileText, Boxes, LogOut, Terminal, Play,
  ChevronLeft, ChevronRight, Network, Zap, Shield
} from "lucide-react";

const NAV = [
  { href: "/dashboard",    label: "Overview",     icon: LayoutDashboard },
  { href: "/dashboard/providers",  label: "Providers",    icon: Server },
  { href: "/dashboard/users",       label: "Users",         icon: Users },
  { href: "/dashboard/models",      label: "Models",        icon: Boxes },
  { href: "/dashboard/routing",     label: "Routing",       icon: GitBranch },
  { href: "/dashboard/analytics",   label: "Analytics",     icon: BarChart3 },
  { href: "/dashboard/logs",        label: "Logs",          icon: Terminal },
  { href: "/dashboard/playground",  label: "Playground",    icon: Play },
  { href: "/dashboard/settings",    label: "Settings",      icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (mounted && !sessionStorage.getItem("ai_gateway_admin")) {
      router.replace("/login");
    }
  }, [mounted, router]);

  const handleLogout = () => {
    sessionStorage.removeItem("ai_gateway_admin");
    sessionStorage.removeItem("ai_gateway_email");
    router.replace("/login");
  };

  if (!mounted) return (
    <div className="min-h-screen bg-[#030711] flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="flex h-screen bg-[#030711] overflow-hidden">
      {/* Sidebar */}
      <aside className={`relative flex flex-col border-r border-white/5 bg-[#0a0f1e] transition-all duration-300 ${collapsed ? "w-16" : "w-56"}`}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-white/5 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shrink-0 shadow-lg shadow-cyan-500/20">
            <Shield className="w-4 h-4 text-white" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">AI Gateway</h1>
              <p className="text-[10px] text-slate-500">Control Panel</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 overflow-y-auto space-y-0.5 px-2">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 group
                  ${active
                    ? "bg-cyan-500/15 text-cyan-400 shadow-inner"
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                  }
                `}
              >
                <Icon className={`w-4 h-4 shrink-0 ${active ? "text-cyan-400" : "text-slate-500 group-hover:text-slate-300"}`} />
                {!collapsed && <span className="truncate">{label}</span>}
                {active && !collapsed && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Collapse toggle + Logout */}
        <div className="border-t border-white/5 p-2 space-y-0.5">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all text-sm"
          >
            {collapsed
              ? <ChevronRight className="w-4 h-4" />
              : <><ChevronLeft className="w-4 h-4" /><span>Collapse</span></>
            }
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/5 transition-all text-sm"
          >
            <LogOut className="w-4 h-4" />
            {!collapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
