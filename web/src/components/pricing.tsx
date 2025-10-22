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
import { useRouter } from "next/navigation";

const tooltipContent = {
  styles: "Choose from a variety of styles to suit your preferences.",
  filters: "Choose from a variety of filters to enhance your portraits.",
  credits: "Use these credits to retouch your portraits.",
};

const YEARLY_DISCOUNT = 20;
const plans = [
  {
    name: "شروع‌کننده",
    price: 1800000,
    priceName: " تومان",
    monthly: "/ماهانه",
    description: "مناسب برای کسب‌وکارهای کوچک و شروع‌کننده",
    features: [
      { title: "تا 250 پیام", messageCount: 250 },
      { title: "7 روز ذخیره سازی فایل ها", storageDays: 7 },
    ],
    buttonText: "ثبت نام",
    isPopular: true,
  },
  {
    name: "حرفه‌ای",
    price: 4200000,
    priceName: " تومان",
    monthly: "/ماهانه",
    isRecommended: true,
    description: "مناسب برای کسب‌وکارهای در حال رشد و متوسط",
    features: [
      { title: "تا 1000 پیام", messageCount: 1000 },
      { title: "10 روز ذخیره سازی فایل ها", storageDays: 10 },
    ],
    buttonText: "ثبت نام",
  },
  {
    name: "ویژه",
    price: " سفارشی",
    description: "راه‌حل سفارشی برای سازمان‌های بزرگ",
    features: [
      { title: "بدون محدودیت پیام" },
      { title: "بدون محدودیت نگه داری در فایل ها" },
    ],
    buttonText: "تماس با فروش",
  },
];

const Pricing = () => {
  const [selectedBillingPeriod, setSelectedBillingPeriod] =
    useState("monthly");
  const router = useRouter();

  const formatPrice = (price: number | string): string => {
    if (typeof price !== "number") return price;
    return price.toLocaleString("fa-IR");
  };

  const getDisplayPrice = (price: number | string): string => {
    if (typeof price !== "number") return price;
    if (selectedBillingPeriod === "yearly") {
      const discount = price * ((100 - YEARLY_DISCOUNT) / 100) * 12;
      return formatPrice(discount);
    }
    return formatPrice(price);
  };

  const getFeatureTitle = (feature: any): string => {
    if (feature.messageCount && selectedBillingPeriod === "yearly") {
      const yearlyCount = feature.messageCount * 12;
      return `تا ${yearlyCount.toLocaleString("fa-IR")} پیام`;
    } else if (feature.storageDays && selectedBillingPeriod === "yearly") {
      const yearlyDays = feature.storageDays * 12;
      return `${yearlyDays.toLocaleString("fa-IR")} روز ذخیره سازی فایل ها`;
    }
    return feature.title;
  };

  const handleButtonClick = (plan: { buttonText: string }) => {
    if (plan.buttonText === "ثبت نام") {
      router.push("/signup");
    }
    if (plan.buttonText === "تماس با فروش") {
        if (typeof window !== "undefined") {
          window.location.href = "tel:+989105860050";
        }

    }
  };

  return (
    <div
      id="pricing"
      className="flex flex-col items-center justify-center py-12 xs:py-20 px-6"
    >
      <h1 className="text-3xl lg:text-[36px] font-bold text-center tracking-tight">
        قیمت‌گذاری
      </h1>
      <Tabs
        value={selectedBillingPeriod}
        onValueChange={setSelectedBillingPeriod}
        className="mt-8"
      >
        <TabsList className="h-11 px-1.5 rounded-full bg-primary/5">
          <TabsTrigger value="monthly" className="py-1.5 rounded-full">
            ماهانه
          </TabsTrigger>
          <TabsTrigger value="yearly" className="py-1.5 rounded-full">
            سالانه ({YEARLY_DISCOUNT.toLocaleString("fa-IR")}%)
          </TabsTrigger>
        </TabsList>
      </Tabs>
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
            <p className="mt-2 text-[20px] font-bold text-primary">
              {getDisplayPrice(plan.price)}
              {plan.priceName}
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
              onClick={() => handleButtonClick(plan)}
            >
              {plan.buttonText}
            </Button>

            <ul className="space-y-2 mt-7">
              {plan.features.map((feature, index) => (
                <li
                  key={`${feature.title}-${index}`}
                  className="flex items-center justify-start gap-1.5 text-sm text-muted-foreground"
                >
                  <CircleCheck className="h-4 w-4 text-green-600" />
                  {getFeatureTitle(feature)}
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
