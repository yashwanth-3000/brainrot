import Navbar from "@/components/ui/navbar";

import { TestLab } from "./test-lab";
import styles from "./test-page.module.css";

export default function TestPage() {
  return (
    <div className={styles.pageShell}>
      <Navbar />
      <TestLab />
    </div>
  );
}
