import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowUpRight, CirclePlay } from "lucide-react";
import React from "react";
import LogoCloud from "./logo-cloud";

const Hero = () => {
  return (
    <div className="min-h-[calc(100vh-6rem)] flex flex-col items-center py-20 px-6">
      <div className="md:mt-6 flex items-center justify-center">
        <div className="text-center max-w-2xl flex flex-col items-center">
          <Badge className="bg-[#E3EEFF] rounded-full py-1 px-3 border-none text-[#1668E3]">
            نسخه 1.0.0 هم‌اکنون در دسترس است
          </Badge>
          <h1 className="mt-6 max-w-[50ch] text-3xl xs:text-4xl sm:text-5xl md:text-5xl font-bold !leading-[1.2] tracking-tight">
            سازمان خود را با هوش مصنوعی دوباره تعریف کنید
          </h1>
          <p className="mt-6 max-w-[80ch] xs:text-lg text-base">
            هوش مصنوعی نکسا به منابع و نرم‌افزارهای سازمانی شما متصل می‌شود و دانش سازمان را در دسترس همه اعضای تیم قرار می‌دهد، تا بهره‌وری و سرعت تصمیم‌گیری افزایش یابد.
          </p>
          <div className="mt-12 flex flex-col sm:flex-row items-center sm:justify-center gap-4">
            <Button
              size="lg"
              className="w-full sm:w-auto rounded-full text-base"
            >
              ثبت نام در لیست انتظار <ArrowUpRight className="!h-5 !w-5" />
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="w-full sm:w-auto rounded-full text-base shadow-none"
            >
              <CirclePlay className="!h-5 !w-5" /> مشاهده دمو
            </Button>
          </div>
        </div>
      </div>
      {/* <LogoCloud className="mt-24 max-w-3xl mx-auto" /> */}
    </div>
  );
};

export default Hero;
