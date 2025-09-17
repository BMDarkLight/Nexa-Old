"use client";

import * as React from "react";
import {
  AudioWaveform,
  BookOpen,
  Bot,
  BotIcon,
  Command,
  Frame,
  GalleryVerticalEnd,
  LogOut,
  Map,
  MessageSquare,
  PieChart,
  Plus,
  Settings,
  Settings2,
  SquareTerminal,
  Unplug,
} from "lucide-react";

import { NavMain } from "@/components/nav-main";
import { NavProjects } from "@/components/nav-projects";
import { NavUser } from "@/components/nav-user";
import { TeamSwitcher } from "@/components/team-switcher";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Button } from "./ui/button";
import Cookie from "js-cookie";

// This is sample data.
type ChatMessage = {
  user: string;
  assistant: string;
  agent_id: string | null;
  agent_name: string;
};
type SessionResponse = {
  session_id: string;
  chat_history: ChatMessage[];
  user_id: string;
};
interface Session {
  id: string;
  title: string;
}
const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.4:8000";
const End_point = "/sessions";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const [sessions, setSession] = React.useState<Session[]>([]);

  // تابع fetch جداگانه برای استفاده مجدد
  const fetchSessions = async () => {
    try {
      const token = Cookie.get("auth_token");
      const tokenType = Cookie.get("token_type");
      const res = await fetch(`${API_Base_Url}${End_point}`, {
        headers: {
          Authorization: `${tokenType} ${token}`,
          "Content-Type": "application/json",
        },
        cache: "no-store",
      });

      if (!res.ok) {
        const data = await res.json();
        console.log(data.detail);
        return;
      }

      const data: SessionResponse[] = await res.json();
      const dataArr: Session[] = data.map((item) => ({
        id: item.session_id,
        title: item.chat_history?.[0]?.user || "گفتگو بدون عنوان",
      }));
      setSession(dataArr);
    } catch (err) {
      console.error(err);
    }
  };

  React.useEffect(() => {
    fetchSessions();
  }, []);

  // Delete Sessions
  const handleDeleteSessions = async (sessionId: string) => {
    try {
      const token = Cookie.get("auth_token");
      const token_type = Cookie.get("token_type");
      const res = await fetch(`${API_Base_Url}${End_point}/${sessionId}`, {
        method: "DELETE",
        headers: {
          Authorization: `${token_type} ${token}`,
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) {
        const data = await res.json();
        console.log(data.detail);
        return;
      }
      setSession((newSess) => newSess.filter((prev) => prev.id !== sessionId));
    } catch (err) {
      console.error(err);
    }
  };

  // اضافه شدن قابلیت رفرش لیست بعد از ایجاد سشن جدید
  const handleNewChat = async () => {
    try {
      const token = Cookie.get("auth_token");
      const token_type = Cookie.get("token_type");
      const res = await fetch(`${API_Base_Url}${End_point}`, {
        method: "POST",
        headers: {
          Authorization: `${token_type} ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const data = await res.json();
        console.log(data.detail);
        return;
      }
      await res.json();
      // بعد از ایجاد سشن جدید، لیست sessionها را دوباره fetch می‌کنیم
      fetchSessions();
    } catch (err) {
      console.error(err);
    }
  };

  const data = {
    user: {
      name: "",
      email: "m@example.com",
      avatar: "/avatars/shadcn.jpg",
    },
    teams: [
      {
        name: "نکسا",
        logo: GalleryVerticalEnd,
        plan: "ورژن 1.0.0",
      },
    ],
    navMain: [
      {
        title: "گفتگوها",
        url: "#",
        icon: MessageSquare,
        isActive: true,
        items: sessions.map((sess) => ({
          id: sess.id,
          title: sess.title,
          url: `/dashboard/chatbot/${sess.id}`,
        })),
      },
    ],
    projects: [
      {
        name: "ایجنت ها",
        url: "/dashboard/agent",
        icon: BotIcon,
        type: "link",
        hasChild: true,
      },
      {
        name: "اتصالات و داده ها",
        url: "/dashboard/connector",
        icon: Unplug,
        type: "link",
        hasChild: false,
      },
      {
        name: "تنظیمات و اعتبار",
        url: "",
        icon: Settings,
        type: "alert",
      },
      {
        name: "خروج از حساب",
        url: "",
        icon: LogOut,
        color: "text-red-600 ",
        type: "action",
      },
    ],
  };

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
        <div className="">
          <Button
            onClick={handleNewChat}
            className="w-full border-1 bg-transparent text-primary cursor-pointer hover:bg-primary hover:text-secondary"
          >
            گفتگو جدید <Plus />
          </Button>
        </div>
      </SidebarHeader>
      <SidebarContent className="flex flex-col justify-between">
        <NavMain items={data.navMain} onDelete={handleDeleteSessions} />
        <NavProjects projects={data.projects} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
