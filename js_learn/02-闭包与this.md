# 02 · 函数、闭包与 this：JS 的灵魂

> 配对练习：`02-closures/` 六题。本章是 C/C++ 经验**最没用**的一章——从零建立心智模型。

## 1. 函数是一等公民

函数可以赋值给变量、存进数组、当参数传、当返回值——相当于函数指针，但**携带环境**（见闭包）：

```js
const f = function (x) { return x * 2; };
const g = (x) => x * 2;        // 箭头函数：更短的函数表达式
[1, 2, 3].map(g);              // 函数当参数传
```

声明方式差异（先记住行为，细节用到再查）：

- `function f() {}`：**声明**，整个函数被提升——定义之前就能调用（编译器先登记）
- `const f = () => {}`：**表达式**，走 `const` 规则（TDZ，定义前访问抛异常）

## 2. 作用域链 → 闭包

变量查找规则：先找自己作用域 → 没有就找**定义时**所在的外层作用域 → 一路找到全局。

**闭包 = 函数 + 其定义处作用域的引用。** 它是语言机制，不是"技巧"——你每次写函数都在创建闭包。

### C++ 对照：lambda 捕获

C++ 里捕获的变量随栈帧销毁，所以想"返回一个有状态的函数"得用 `shared_ptr` 伪装：

```cpp
auto makeCounter = []() {
    auto count = std::make_shared<int>(0);   // 手动延长生命周期
    return [count]() { return ++*count; };
};
```

JS **没有栈帧销毁**——被闭包引用的变量自动活到最后一个引用它的闭包死掉为止：

```js
function makeCounter() {
  let count = 0;            // 这个变量"逃出"了函数，没人需要操心它的生命周期
  return () => ++count;
}
const next = makeCounter();
next(); next();             // 1, 2
```

### 闭包的标准用途：私有状态

`02-closures/` 里 once / memoize / debounce 三道题，本质是同一件事——**用闭包当私有成员变量**：

```js
function debounce(fn, wait) {
  let timerId = null;                        // ← 闭包私有状态，外部摸不到
  return (...args) => {
    clearTimeout(timerId);                   // ...args：把所有参数"打包/解包"
    timerId = setTimeout(() => fn(...args), wait);
  };
}
```

`(...args)` 是"剩余参数"语法，相当于把函数指针调用时的可变参数变得类型安全（比 C 的 `va_list` 优雅得多）。

记忆锚点：**每个闭包环境是独立的**——练习 01-counter 的第二个测试就是验证这件事（两个计数器互不干扰）。

## 3. this：运行时绑定

### 与 C++ 的根本差异

C++：`this` 在**编译期**绑定到成员函数所属的类，写 `obj.method()` 还是存函数指针调用，`this` 都是那个对象。

JS：`this` 是**每次调用的上下文**，由**调用方式**在运行时决定。同一个函数，谁调用它，`this` 就是谁。

### 四条规则（默背）

```js
function show() { return this.name; }
const o = { name: 'o', show };

o.show();                     // 规则1：obj.fn() → this = obj ——→ 'o'
show();                       // 规则2：裸调用 → 非严格模式 this = globalThis（通常取不到东西）
                              //         严格模式 / ESM 中是 undefined，直接报错
o.show.call({ name: 'x' });   // 规则3a：call/apply → 显式指定，当场生效 ——→ 'x'
const bound = show.bind({ name: 'y' });
bound();                      // 规则3b：bind → 产生永久绑定的新函数 ——→ 'y'

const timer = {
  name: 'timer',
  start() {
    setTimeout(() => show.call(this), 0);   // 规则4：箭头函数没有自己的 this，
  },                                        //        继承【定义处】外层的 this
};
```

记忆锚点：**箭头函数没有 this，向外借。**

- `call(实参逐个传)` vs `apply(实参放数组里)`：功能相同，传参方式不同
- `bind` 不调用，只生产"绑定死的新函数"

规则 2 是 bug 高发区——方法脱离对象再调用（比如存成回调传给别人），`this` 就丢了。练习 05-this 会让你亲手修复一次。

### 实战守则（消灭 90% 的 this 问题）

1. 方法内的回调要访问 `this` → **箭头函数**
2. 要把方法安全地传出去 → **先 `bind`**
3. 看到老代码里 `const self = this` → 那是箭头函数普及前的考古层

## 4. 原型与 class：20 分钟版本

### 原型链：属性的查找路径

JS 对象大多有一个隐藏链接（原型）指向另一个对象。**访问自己没有的属性时，沿链向上找**：

```js
const animal = { eats: true };
const cat = Object.create(animal);   // cat 的原型是 animal
cat.meows = true;

cat.meows;   // true  —— 自己的
cat.eats;    // true  —— 沿原型链"借"来的，但只读：给 cat.eats 赋值会在 cat 上创建新属性
```

这就是"方法"省内存的原理：方法挂在共享的原型对象上，而不是每个实例一份。

### class：原型的语法糖

```js
class Cat {
  constructor(name) { this.name = name; }
  meow() { return this.name + ': 喵'; }
}

new Cat('a').meow === new Cat('b').meow;   // true —— 方法在 Cat.prototype 上，所有实例共享一份
```

**`new Cat('x')` 做了什么**（3 步）：

1. 创建空对象
2. 把它的原型链到 `Cat.prototype`
3. 以新对象为 `this` 调用 `constructor`

不需要深挖 `__proto__` 与 `prototype` 的区别——现代代码写 `class` 就够了。但要知道：**JS 的 class 没有类拷贝语义、没有方法重载**，构造器只能有一个。

## 5. 组合技：EventEmitter

`02-closures/06-event-emitter.js` 是本章综合考：class（原型）+ Map（第一章）+ 回调（一等公民函数）+ `...args`（剩余参数）。Node 里所有流、HTTP、文件 IO 都基于这个模式（内置 `events` 模块），等价于 C++ 的观察者模式/信号槽，但代码量只有十分之一。

## 6. 做练习

| 文件 | 考点 |
|---|---|
| `01-counter.js` | 闭包基础：私有状态、环境独立 |
| `02-once.js` | 闭包 + 布尔门闩 |
| `03-memoize.js` | 闭包 + 缓存（动态规划的味道） |
| `04-debounce.js` | 闭包 + 定时器（前端最常用面试题） |
| `05-this.js` | 四条规则实操：bind / call / apply / 箭头函数 |
| `06-event-emitter.js` | 全章综合 |

## 7. 自测（答案在下方）

1. 闭包环境何时销毁？
2. `obj.method()` 和 `const m = obj.method; m()` 的 `this` 分别是什么？
3. 为什么 `setTimeout(function(){ this.x }, 0)` 常常出错，改成箭头函数为什么就好了？
4. `new Foo()` 的三步是什么？

<details>
<summary>答案</summary>

1. 当所有引用该函数的变量/引用都消失时（GC 按可达性回收，没有引用计数）。
2. 前者是 `obj`；后者脱离了调用者——非严格模式下是 `globalThis`，严格模式 `undefined`。
3. 定时器回调是"裸调用"（规则2），普通函数的 `this` 丢失；箭头函数没有自己的 `this`，继承外层方法调用时的 `this`，即对象本身。
4. 创建空对象 → 原型链到 `Foo.prototype` → 以新对象为 `this` 调用构造函数。
</details>
