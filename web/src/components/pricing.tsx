"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { CircleCheck, CircleHelp } from "lucide-react";
import { useState } from "react";

const tooltipContent = {
  styles: "Choose from a variety of styles to suit your preferences.",
  filters: "Choose from a variety of filters to enhance your portraits.",
  credits: "Use these credits to retouch your portraits.",
};

const YEARLY_DISCOUNT = 20;
const plans = [
  {
    name: "شروع‌کننده",
    price: "1,800,000 تومان ",
    monthly: "/ماهانه" ,
    description:
      "مناسب برای کسب‌وکارهای کوچک و شروع‌کننده",
    features: [
      { title: "تا 250 پیام" },
      { title: "7 روز ذخیره سازی فایل ها" },
    ],
    buttonText: "ثبت نام",
    isPopular: true,
  },
  {
    name: "حرفه‌ای",
    price: "4,200,000 تومان ",
    monthly: "/ماهانه" ,
    isRecommended: true,
    description:
      "مناسب برای کسب‌وکارهای در حال رشد و متوسط",
    features: [
      { title: "تا 1000 پیام" },
      { title: "10 روز ذخیره سازی فایل ها" },
    ],
    buttonText: "ثبت نام",
  },
  {
    name: "ویژه",
    price: " سفارشی",
    description:
      "راه‌حل سفارشی برای سازمان‌های بزرگ",
    features: [
      { title: "بدون محدودیت پیام" },
      { title: "بدون محدودیت نگه داری در فایل ها" },
    ],
    buttonText: "تماس با فروش",
  },
];

const Pricing = () => {
  const [selectedBillingPeriod, setSelectedBillingPeriod] = useState("monthly");

  return (
    <div
      id="pricing"
      className="flex flex-col items-center justify-center py-12 xs:py-20 px-6"
    >
      <h1 className="text-3xl xs:text-4xl md:text-5xl font-bold text-center tracking-tight">
        قیمت‌گذاری
      </h1>
      <div className="mt-5 font-medium">
        <p className="text-[#585858] text-lg">ماهانه - سالانه (۲۰ درصد تخفیف)</p>
      </div>
      {/* <Tabs
        value={selectedBillingPeriod}
        onValueChange={setSelectedBillingPeriod}
        className="mt-8"
      >
        <TabsList className="h-11 px-1.5 rounded-full bg-primary/5">
          <TabsTrigger value="monthly" className="py-1.5 rounded-full">
            Monthly
          </TabsTrigger>
          <TabsTrigger value="yearly" className="py-1.5 rounded-full">
            Yearly (Save {YEARLY_DISCOUNT}%)
          </TabsTrigger>
        </TabsList>
      </Tabs> */}
      <div className="mt-12 max-w-screen-lg mx-auto grid grid-cols-1 lg:grid-cols-3 items-center gap-8">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={cn("relative border rounded-xl p-6 bg-background/50", {
              "border-[2px] border-primary bg-background": plan.isPopular,
            })}
          >
            {plan.isPopular && (
              <Badge className="absolute top-0 right-1/2 translate-x-1/2 -translate-y-1/2">
                محبوب ترین
              </Badge>
            )}
            <h3 className="text-base font-bold">{plan.name}</h3>
            <p className="mt-2 text-lg font-bold text-primary">
              
              {plan.price} 
              <span className="ml-1.5 text-sm text-muted-foreground font-normal">
                {plan.monthly}
              </span>
            </p>
            <p className="mt-4 font-medium text-muted-foreground text-sm">
              {plan.description}
            </p>

            <Button
              variant={plan.isPopular ? "default" : "outline"}
              size="lg"
              className="w-full mt-6 text-base rounded-full cursor-pointer"
            >
              {plan.buttonText}
            </Button>
            {/* <Separator className="my-8" /> */}
            <ul className="space-y-2 mt-7">
              {plan.features.map((feature) => (
                <li key={feature.title} className="flex items-start gap-1.5 text-sm text-muted-foreground">
                  {/* <CircleCheck className="h-4 w-4 mt-1 text-green-600" /> */}
                  {feature.title}
                  {/* {feature.tooltip && (
                    <Tooltip>
                      <TooltipTrigger className="cursor-help">
                        <CircleHelp className="h-4 w-4 mt-1 text-gray-500" />
                      </TooltipTrigger>
                      <TooltipContent>{feature.tooltip}</TooltipContent>
                    </Tooltip>
                  )} */}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Pricing;
