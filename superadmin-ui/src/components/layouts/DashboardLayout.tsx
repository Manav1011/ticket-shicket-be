import { Outlet } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  TicketIcon,
  LayoutDashboardIcon,
  LogOutIcon,
} from "lucide-react";
import { authService } from "@/services/authService";
import { useNavigate } from "react-router-dom";

const mainNavItems = [
  {
    title: "B2B Requests",
    icon: TicketIcon,
    href: "/dashboard",
    isActive: true,
  },
];

function DashboardSidebar() {
  const navigate = useNavigate();

  const handleLogout = () => {
    authService.logout();
    navigate("/login");
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="Ticket Shicket"
              className="data-[active=true]:bg-sidebar-accent"
            >
              <LayoutDashboardIcon data-icon="inline-start" />
              <span className="font-semibold">Ticket Shicket</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Main</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    tooltip={item.title}
                    isActive={item.isActive}
                    onClick={() => navigate(item.href)}
                  >
                    <item.icon data-icon="inline-start" />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              tooltip="Logout"
              onClick={handleLogout}
              className="text-muted-foreground"
            >
              <LogOutIcon data-icon="inline-start" />
              <span>Logout</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}

export function DashboardLayout() {
  return (
    <SidebarProvider>
      <DashboardSidebar />
      <SidebarTrigger />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </SidebarProvider>
  );
}