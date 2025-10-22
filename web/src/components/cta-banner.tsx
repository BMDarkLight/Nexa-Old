import { ArrowUpRight, Forward } from "lucide-react";
import { Button } from "./ui/button";
import { AnimatedGridPattern } from "./ui/animated-grid-pattern";
import { cn } from "@/lib/utils";

export default function CTABanner() {
  return (
    <div className="px-6">
      <div className="dark:border relative overflow-hidden my-20 w-full dark bg-[#001120] text-foreground max-w-screen-lg mx-auto rounded-2xl py-10 md:py-10 px-6 md:px-14">
        <div className="relative z-0 flex flex-col gap-3">
          <h3 className="text-2xl md:text-[30px] font-semibold">
            افزایش بهره‌وری سازمان ها در عصر هوش مصنوعی
          </h3>
          <p className="mt-3 text-base md:text-[14px]">
            در این کتابچه با روش‌های ساده و عملی هوش مصنوعی برای استفاده های سازمانی آشنا می‌شوید و یاد می‌گیرید چگونه سازمان خود را به هوش مصنوعی مجهز کنید.
          </p>
        </div>
        <div className="relative z-0 mt-6 flex flex-col sm:flex-row gap-4">
          <Button size="lg" className="text-white rounded-full ">
           دانلود رایگان کتابچه <ArrowUpRight className="!h-5 !w-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
