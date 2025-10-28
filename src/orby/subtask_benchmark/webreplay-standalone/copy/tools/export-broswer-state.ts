function exportSessionStorage() {
  return Object.fromEntries(Object.entries(sessionStorage));
}

function exportLocalStorage() {
  return Object.fromEntries(Object.entries(localStorage));
}

export function exportCookies() {
  const cookies = document.cookie.split('; ');

  // Format cookies as specified
  const formattedCookies = cookies.map((cookieString) => {
    const [name, value] = cookieString.split('=');

    // Return the formatted cookie object
    // We cannot get the domain from browser cookies, so we use the current domain
    // In the future we will integrate it to use playwright, then we can get the domain
    return {
      name: name,
      value: value,
      domain: window.location.hostname,
      path: '/',
      secure: true,
    };
  });
  return formattedCookies;
}
