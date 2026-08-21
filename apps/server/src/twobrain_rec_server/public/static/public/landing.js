document.documentElement.classList.add('enhanced');

const menuButton = document.querySelector('[data-menu-button]');
const mobileNav = document.querySelector('[data-mobile-nav]');

if (menuButton && mobileNav) {
  menuButton.addEventListener('click', () => {
    const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
    menuButton.setAttribute('aria-expanded', String(!isOpen));
    mobileNav.classList.toggle('open', !isOpen);
  });

  mobileNav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      menuButton.setAttribute('aria-expanded', 'false');
      mobileNav.classList.remove('open');
    });
  });
}

const header = document.querySelector('[data-header]');
const updateHeader = () => header?.classList.toggle('scrolled', window.scrollY > 24);
updateHeader();
window.addEventListener('scroll', updateHeader, { passive: true });

const billingButtons = document.querySelectorAll('[data-period]');
const price = document.querySelector('[data-price-value]');
const pricePeriod = document.querySelector('[data-price-period-value]');
const priceNote = document.querySelector('[data-price-note-value]');

billingButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const period = button.dataset.period;
    if (!period || !button.dataset.price || !price || !pricePeriod || !priceNote) return;

    billingButtons.forEach((item) => {
      const selected = item === button;
      item.classList.toggle('active', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    price.textContent = button.dataset.price;
    pricePeriod.textContent = button.dataset.pricePeriod || '';
    priceNote.textContent = button.dataset.priceNote || '';
  });
});

document.querySelectorAll('[data-product-tabs]').forEach((tabsRoot) => {
  const tabs = [...tabsRoot.querySelectorAll('[role="tab"]')];
  const panels = [...tabsRoot.querySelectorAll('[role="tabpanel"]')];

  const activateTab = (nextTab, focus = false) => {
    const target = nextTab.dataset.tab;
    tabs.forEach((tab) => {
      const selected = tab === nextTab;
      tab.classList.toggle('active', selected);
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel) => {
      const selected = panel.dataset.panel === target;
      panel.hidden = !selected;
      panel.classList.toggle('active', selected);
    });
    if (focus) nextTab.focus();
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = tabs.length - 1;
      activateTab(tabs[nextIndex], true);
    });
  });

  activateTab(tabs.find((tab) => tab.getAttribute('aria-selected') === 'true') || tabs[0]);
});

const revealItems = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 },
  );
  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add('visible'));
}
