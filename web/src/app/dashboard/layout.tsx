import React from "react";
import { AppSidebar } from "@/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import H2Tag from "@/components/H2Tag";
import { ChatProvider } from "./context/ChatContext";
import ToastProvider from "@/components/ToasterProvider";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <SidebarProvider dir="rtl">
      <AppSidebar />
      <SidebarInset>
        <header className="sticky top-0 z-50 bg-background flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12 md:hidden border-b-1">
          <div className="flex items-center justify-between w-full gap-2 px-4">
            <SidebarTrigger className="-mr-1" />
            <H2Tag />
          </div>
        </header>
        <div className="flex flex-col gap-10 p-4 pt-0">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
