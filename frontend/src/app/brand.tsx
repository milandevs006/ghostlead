import Image from 'next/image';
import styles from './brand.module.css';
export default function Brand({large=false,loading=false}:{large?:boolean;loading?:boolean}){
 return <div className={`${styles.brand} ${large?styles.large:''} ${loading?styles.loading:''}`} role="img" aria-label="GhostLead"><Image className={styles.icon} src="/brand/shield.png" alt="" width={52} height={52} unoptimized/><Image className={styles.word} src="/brand/wordmark.png" alt="" width={190} height={40} unoptimized/></div>;
}
