import React from "react";
import type { Metadata } from "next";
import "./globals.css";
import localFont from "next/font/local";
import { AppSidebar } from "@/components/app-sidebar"
import { ThemeProvider } from "next-themes";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import H2Tag from "@/components/H2Tag";
import { SessionProvider } from "./dashboard/context/sessionContext";
import { Toaster } from "sonner";
import ToastProvider from "@/components/ToasterProvider";


const myFont = localFont({
  src: [
    {
      path: '../../public/fonts/IRANYekanX-Regular.woff2',
      weight: '400',
      style: 'normal',
    }
  ]
});

export const metadata: Metadata = {
  title: "Nexa",
  description: "Nexa",
  icons : {
    icon: "/Squad/Login/logo.png"
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={myFont.className}>
             <SessionProvider>
              {children}
             </SessionProvider>
             <ToastProvider />
      </body>
    </html>
  );
}
