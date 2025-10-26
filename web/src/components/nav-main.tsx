"use client";

import {
  ChevronLeft,
  Edit,
  MoreVertical,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { useState } from "react";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import Swal from "sweetalert2";

export function NavMain({
  items,
  onDelete,
}: {
  items: {
    title: string;
    url: string;
    icon?: LucideIcon;
    isActive?: boolean;
    items?: {
      title: string;
      url: string;
      id: string;
    }[];
  }[];
  onDelete?: (sessionId: string) => void;
}) {
  const pathname = usePathname();
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  return (
    <SidebarGroup>
      <SidebarMenu>
        {items.map((item) => (
          <Collapsible
            key={item.title}
            asChild
            defaultOpen={item.isActive}
            className="group/collapsible"
          >
            <SidebarMenuItem>
              <CollapsibleTrigger asChild>
                <SidebarMenuButton
                  tooltip={item.title}
                  className="text-[#71717A] text-base"
                >
                  {item.icon && <item.icon />}
                  <span>{item.title}</span>
                  <ChevronLeft className="mr-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-[-90deg]" />
                </SidebarMenuButton>
              </CollapsibleTrigger>
              <CollapsibleContent className="overflow-x-hidden">
                <SidebarMenuSub className="w-full max-w-full overflow-x-hidden">
                  {item.items?.map((subItem) => {
                    const isActive = pathname === subItem.url;
                    return (
                      <SidebarMenuSubItem key={subItem.id} className="w-full max-w-full overflow-x-hidden">
                        <SidebarMenuSubButton
                          asChild
                          className={cn(
                            "text-[#71717A] w-full !px-4 !py-2 max-w-full overflow-x-hidden",
                            isActive &&
                              "bg-primary/50 text-[#001120] hover:bg-primary/70 hover:text-[#001120] rounded-md"
                          )}
                        >
                          <div 
                            className="flex justify-between items-center text-base w-full min-w-0 max-w-full overflow-x-hidden"
                            style={{ maxWidth: '100%' }}
                          >
                            <div className="hover:text-sidebar-accent-foreground active:text-sidebar-accent-foreground flex-1 min-w-0 mr-2 overflow-x-hidden">
                              <a href={subItem.url} className="block w-full max-w-full overflow-x-hidden">
                                <span className="block truncate w-full max-w-full">{subItem.title}</span>
                              </a>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <DropdownMenu 
                                open={openDropdown === subItem.id} 
                                onOpenChange={(open) => setOpenDropdown(open ? subItem.id : null)}
                              >
                                <DropdownMenuTrigger asChild>
                                  <button className="text-black cursor-pointer p-1 rounded-md hover:bg-sidebar-accent transition-colors">
                                    <MoreVertical size={16} />
                                  </button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    onClick={async (e) => {
                                      e.preventDefault();
                                      setOpenDropdown(null); // بستن dropdown قبل از نمایش popup
                                      if (onDelete && subItem.id) {
                                        const result = await Swal.fire({
                                          title: "حذف گفتگو",
                                          text: "آیا مطمئن هستید که می‌خواهید این گفتگو را حذف کنید؟",
                                          showCancelButton: true,
                                          cancelButtonText: "انصراف",
                                          confirmButtonText: "حذف",
                                          reverseButtons: true,
                                          customClass: {
                                            popup: "swal-rtl",
                                            title: "swal-title",
                                            confirmButton: "swal-confirm-btn swal-half-btn",
                                            cancelButton: "swal-cancel-btn swal-half-btn",
                                            htmlContainer: "swal-text",
                                            actions: "swal-container"
                                          }
                                        });

                                        if (result.isConfirmed) {
                                          onDelete(subItem.id);
                                        }
                                      }
                                    }}
                                    className="text-black hover:text-red-500 cursor-pointer"
                                  >
                                    <Trash2 size={16} className="mr-2 group-hover:text-red-500 " />
                                    حذف گفتگو
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </div>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    );
                  })}
                </SidebarMenuSub>
              </CollapsibleContent>
            </SidebarMenuItem>
          </Collapsible>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
