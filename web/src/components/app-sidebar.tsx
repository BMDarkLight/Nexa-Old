"use client";

import * as React from "react";
import {
  BotIcon,
  GalleryVerticalEnd,
  LogOut,
  MessageSquare,
  Plus,
  Settings,
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
import { usePathname, useRouter } from "next/navigation";

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
  title?: string | null;
};
interface Session {
  id: string;
  title: string;
}
interface UserData {
  username: string;
  firstname: string;
  lastname: string;
  email: string;
}

const API_Base_Url =
  process.env.NEXT_PUBLIC_SERVER_URL ?? "http://62.60.198.65";
const API_PORT = process.env.NEXT_PUBLIC_API_PORT ?? "8000";
const End_point = "/sessions";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const [sessions, setSession] = React.useState<Session[]>([]);
  const [userEmail, setUserEmail] = React.useState<string>("m@example.com");
  const [authHeader, setAuthHeader] = React.useState<string>("");

  const pathname = usePathname();
  const router = useRouter();

  React.useEffect(() => {
    const token = Cookie.get("auth_token");
    const tokenType = Cookie.get("token_type") ?? "Bearer";
    if (token) {
      setAuthHeader(`${tokenType} ${token}`);
    }
  }, []);

  const fetchSessions = async () => {
    if (!authHeader) return;
    try {
      const res = await fetch(`${API_Base_Url}:${API_PORT}${End_point}`, {
        headers: {
          Authorization: authHeader,
          "Content-Type": "application/json",
        },
        cache: "no-store",
      });

      if (!res.ok) return;

      const data: SessionResponse[] = await res.json();

      const dataArr: Session[] = data.map((item) => {
        let titleText = "گفتگو جدید";

        if (item.title && typeof item.title === "string" && item.title.trim() !== "") {
          titleText = item.title;
        }

        if (titleText.length > 20) {
          titleText = titleText.slice(0, 15) + "…";
        }

        return {
          id: item.session_id,
          title: titleText,
        };
      });

      setSession(dataArr.reverse());
    } catch {
      console.error("خطا در دریافت گفتگوها");
    }
  };

  React.useEffect(() => {
    fetchSessions();
  }, [authHeader]);

  React.useEffect(() => {
    if (pathname.startsWith("/dashboard/chatbot/")) {
      fetchSessions();
    }
  }, [pathname]);

  React.useEffect(() => {
    const interval = setInterval(() => {
      fetchSessions();
    }, 10000); // هر 10 ثانیه
    return () => clearInterval(interval);
  }, [authHeader]);

  React.useEffect(() => {
    if (!authHeader) return;
    const fetchUserEmail = async () => {
      try {
        const res = await fetch(`${API_Base_Url}:${API_PORT}/users`, {
          headers: {
            Authorization: authHeader,
            "Content-Type": "application/json",
          },
          cache: "no-store",
        });
        if (!res.ok) return;
        const data: UserData[] = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setUserEmail(data[0].email || "m@example.com");
        }
      } catch {
        console.error("خطا در دریافت اطلاعات کاربر");
      }
    };
    fetchUserEmail();
  }, [authHeader]);

  // Delete Sessions
  const handleDeleteSessions = async (sessionId: string) => {
    if (!authHeader) return;
    try {
      const res = await fetch(
        `${API_Base_Url}:${API_PORT}${End_point}/${sessionId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: authHeader,
            "Content-Type": "application/json",
          },
        }
      );
      if (!res.ok) {
        alert("خطا در حذف گفتگو. لطفاً دوباره تلاش کنید");
        return;
      }
      setSession((newSess) => newSess.filter((prev) => prev.id !== sessionId));

      if (pathname === `/dashboard/chatbot/${sessionId}`) {
        router.push("/dashboard");
      }
    } catch {
      alert("خطا در ارتباط با سرور. لطفاً دوباره تلاش کنید");
    }
  };

  const handleNewChat = () => {
    router.push("/dashboard");
  };

  const data = {
    user: {
      name: "",
      email: userEmail,
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
