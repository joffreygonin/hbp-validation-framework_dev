export function downloadJSON(json, filename) {
    const blob = new Blob([json], { type: 'application/json' });

    /* taken from react-csv */
    if (navigator && navigator.msSaveOrOpenBlob) {
      navigator.msSaveOrOpenBlob(blob, filename);
    } else {
      const dataURI = `data:application/json;charset=utf-8,${json}`;

      const URL = window.URL || window.webkitURL;
      const downloadURI = typeof URL.createObjectURL === 'undefined' ? dataURI : URL.createObjectURL(blob);
      let link = document.createElement('a');
      link.setAttribute('href', downloadURI);
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
}


export function formatAuthors(authors) {
    if (authors) {
      return authors.map(author => (author.given_name + " " + author.family_name)).join(", ");
    } else {
      return "";
    }
}


export function formatTimeStampToLongString(ISOtimestamp) {
  if (ISOtimestamp) {
    const d = new Date(ISOtimestamp);
    return d.toUTCString();
  } else {
      return "";
  }
}


export function formatTimeStampToCompact(ISOtimestamp) {
  if (ISOtimestamp) {
    const d = new Date(ISOtimestamp);
    return d.toISOString().
            replace(/T/, ' ').      // replace T with a space
            replace(/\..+/, '')     // delete the dot and everything after;
  } else {
      return "";
  }
}


export function roundFloat(value, places) {
  return `${value.toFixed(places)}`;
}