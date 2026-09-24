/* Random task, just for fun. A shuffled bag, so repeated rolls visit every task before any comes round again. */
import {taskOrder} from '@/lib/bench';

let bag = [];
export function nextTask(current) {
  const all = taskOrder();
  if (all.length < 2) return all[0];
  if (!bag.length) { bag = [...all]; for (let i = bag.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [bag[i], bag[j]] = [bag[j], bag[i]]; } }
  if (bag[bag.length - 1] === current) bag.unshift(bag.pop());
  return bag.pop();
}
