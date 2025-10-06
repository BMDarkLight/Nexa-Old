import {
  Blocks,
  Bot,
  ChartPie,
  Film,
  HeartHandshake,
  Lock,
  MessageCircle,
  Settings2,
  SlidersHorizontal,
  Timer,
  Unplug,
  UserRoundMinus,
} from "lucide-react";
import LogoCloud from "./logo-cloud";
import React from "react";

const features = [
  {
    icon: Unplug,
    iconColor: "text-[#2A9D90]",
    title: "یکپارچه با منابع شما",
    description:
      "از دیتابیس تا Google Workspace و فایل‌های داخلی؛ همه به نکسا وصل می‌شوند.",
  },
  {
    icon: Timer,
    iconColor: "text-[#FFC727]",
    title: "افزایش سرعت جستجو",
    description:
      "سؤال خود را بپرسید و فوری گزارش بگیرید؛ بدون نیاز به ساعت ها جستجو.",
  },
  {
    icon: Lock,
    iconColor: "text-[#DC2626]",
    title: "امنیت و سطح دسترسی",
    description:
      "اطلاعات شما امن می‌ماند و دسترسی‌ها بر اساس نقش‌ها و سطح مجاز هر کاربر تنظیم می‌شود.",
  },
  {
    icon: HeartHandshake,
    iconColor: "text-[#0088FF]",
    title: "آماده‌سازی سریع نیروهای جدید",
    description:
      "به تازه‌واردها کمک می‌کند سریع با دانش سازمان آشنا شوند و بدون اتلاف وقت وارد کار شوند.",
  },
  {
    icon: UserRoundMinus,
     iconColor: "text-[#E76E50]",
    title: "کاهش وابستگی به افراد خاص",
    description:
      "دانش سازمانی در دسترس همه است و تیم کمتر به یک یا چند نفر محدود می‌شود.",
  },
  {
    icon: SlidersHorizontal,
    iconColor: "text-[#6155F5]",
    title: "شخصی‌سازی برای تیم‌های مختلف",
    description:
      "نکسا با ایجنت‌ها و پرامپت‌های اختصاصی، برای هر تیم دانش و عملکرد AI را متناسب می‌کند.",
  },
];

const Features = () => {
  return (
    <div id="features" className="w-full py-12 xs:py-20 px-6">
      <h2 className="text-3xl xs:text-4xl sm:text-5xl font-bold tracking-tight text-center">
        ویژگی‌های نکسا
      </h2>
      <div className="w-full max-w-screen-lg mx-auto mt-10 sm:mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="flex flex-col bg-background border rounded-xl py-6 px-5"
          >
            <div className="mb-3 h-10 w-10 flex items-center justify-center bg-accent rounded-md p-1">
              <feature.icon className={`h-6 w-6 ${feature.iconColor}`} />
            </div>
            <span className="text-lg font-semibold">{feature.title}</span>
            <p className="mt-1 text-foreground/80 text-[15px]">
              {feature.description}
            </p>
          </div>
        ))}
      </div>
      <LogoCloud className="mt-24 max-w-3xl mx-auto" />
    </div>
  );
};

export default Features;
