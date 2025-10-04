import {
  BadgeDollarSign,
  BadgeHelp,
  BookUp,
  BrainCircuit,
  Lightbulb,
  PackageOpen,
  Route,
  Server,
  ShieldCheck,
  Truck,
  Undo2,
  UserRoundCheck,
} from "lucide-react";

const faq = [
  {
    icon: BadgeHelp,
    iconColor: "#FFC727" ,
    question: "نکسا دقیقاً چه کاری انجام می‌دهد؟",
    answer:
      "نکسا یک چت‌بات هوش مصنوعی در اختیار اعضای کلیدی سازمان قرار می‌دهد که به همه منابع و نرم افزار های سازمانی شما متصل و مسلط است.",
  },
  {
    icon: BookUp,
    iconColor: "#2A9D90" ,
    question: "چطور نکسا به افزایش بهره‌وری سازمان ما کمک می‌کند؟",
    answer:
      "نکسا با اتصال به منابع سازمانی، دانش را در اختیار همه می‌گذارد تا کارها سریع‌تر پیش برود و همکاری مؤثرتر شود",
  },
  {
    icon: Server,
     iconColor: "#0088FF" ,
    question: "می‌توانم برای امنیت بیشتر نکسا را روی مدل لوکال اجرا کنم؟",
    answer:
      "بله، در پلن ویژه این امکان وجود دارد. برای جزئیات و راه‌اندازی، با تیم ما تماس بگیرید.",
  },
  {
    icon: PackageOpen,
    iconColor: "#DC2626" ,
    question: "آیا امکان تست رایگان یا دموی محصول وجود دارد؟",
    answer:
      "بله، می‌توانید قبل از خرید، نسخه آزمایشی یا دموی نکسا را امتحان کنید تا با امکانات و عملکرد آن آشنا شوید.",
  },
  {
    icon: BrainCircuit,
    iconColor: "#E76E50" ,
    question: "برای کار با نکسا نیاز به دانش خاصی دارم؟",
    answer:
      "خیر، نکسا به گونه‌ای طراحی شده تا بدون دانش فنی همه اعضای سازمان بتوانند از آن استفاده کنند.",
  },
  {
    icon: Lightbulb,
    iconColor: "#6155F5" ,
    question: "مهم ترین کاربردهای نکسا چیست؟",
    answer:
      "کمک در فرایند های پشتیبانی و بازاریابی، تحلیل داده برای مدیران و آنبوردینگ نیروهای جدید سازمان.",
  },
];

const FAQ = () => {
  return (
    <div
      id="faq"
      className="min-h-screen flex items-center justify-center px-6 py-12 xs:py-20"
    >
      <div className="max-w-screen-lg">
        <h2 className="text-3xl xs:text-4xl md:text-5xl !leading-[1.15] font-bold tracking-tight text-center">
          سوالات پرتکرار
        </h2>
        <p className="mt-3 xs:text-lg text-center text-muted-foreground">
         به پرتکرار ترین سوالات شما پاسخ داده ایم.
        </p>

        <div className="mt-12 grid md:grid-cols-2 gap-3 ">
          {faq.map(({ question, answer, icon: Icon , iconColor }) => (
            <div key={question} className="border p-4 rounded-xl">
              <div className="h-8 w-8 xs:h-10 xs:w-10 flex items-center justify-center rounded-full bg-accent">
                <Icon className={`h-5 w-5 xs:h-6 xs:w-6 text-[${iconColor}]`} />
              </div>
              <div className="mt-2 mb-2 flex items-start gap-2 text-base xs:text-[1.35rem] font-semibold tracking-tight">
                <span>{question}</span>
              </div>
              <p className="text-sm xs:text-base">{answer}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FAQ;
