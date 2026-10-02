export type FavouriteKind='italiana'|'finali'|'svizzero';
export type Favourite={id:string;name:string;mode?:'ko'|'groups'};
export type Favourites=Partial<Record<FavouriteKind,Favourite>>;

export function removeFavourite(current:Favourites,kind:FavouriteKind,id?:string):Favourites{
  if(!current[kind]||(id&&current[kind]?.id!==id))return current;
  const next={...current};
  delete next[kind];
  return next;
}

export function reconcileFavourite(current:Favourites,kind:FavouriteKind,items:Favourite[]):Favourites{
  const selected=current[kind];
  if(!selected)return current;
  const found=items.find(item=>item.id===selected.id);
  if(!found)return removeFavourite(current,kind,selected.id);
  return found.name===selected.name?current:{...current,[kind]:{id:found.id,name:found.name}};
}
