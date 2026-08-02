import { Heart } from 'lucide-react';
import { classNames } from '../lib/utils';
import { useFavorites } from '../hooks/useFavorites';

export function FavoriteButton({
  articleKey,
  compact = false,
}: {
  articleKey: string;
  compact?: boolean;
}) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const favorite = isFavorite(articleKey);

  return (
    <button
      type="button"
      className={classNames('favorite-button', favorite && 'active')}
      aria-pressed={favorite}
      aria-label={favorite ? 'Remove from favorites' : 'Add to favorites'}
      onClick={() => toggleFavorite(articleKey)}
    >
      <Heart
        size={17}
        strokeWidth={2.1}
        fill={favorite ? 'currentColor' : 'none'}
        aria-hidden="true"
      />
      {compact ? null : favorite ? 'Saved' : 'Save'}
    </button>
  );
}
